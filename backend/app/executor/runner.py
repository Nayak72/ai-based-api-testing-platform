import asyncio

import structlog
from bson import ObjectId

from app.db.models import RequestSent, ResponseReceived, RunConfig, TestCaseInDB, TestResultBase
from app.db.repositories import result_repository, run_repository, test_case_repository
from app.executor.engine import TestExecutor

logger = structlog.get_logger()


class RunContext:
    def __init__(self, run_id: ObjectId, config: RunConfig):
        self.run_id = run_id
        self.config = config
        self.in_flight_tasks: dict[str, asyncio.Task] = {}
        self.cancelled = False
        self.cancel_timeout = 10.0

    def add_task(self, test_case_id: str, task: asyncio.Task):
        self.in_flight_tasks[test_case_id] = task

    def remove_task(self, test_case_id: str):
        self.in_flight_tasks.pop(test_case_id, None)

    async def cancel_all(self):
        self.cancelled = True
        if self.in_flight_tasks:
            done, pending = await asyncio.wait(
                self.in_flight_tasks.values(),
                timeout=self.cancel_timeout,
                return_when=asyncio.ALL_COMPLETED,
            )
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

    def is_cancelled(self) -> bool:
        return self.cancelled


class RunOrchestrator:
    def __init__(self):
        self.active_runs: dict[str, RunContext] = {}

    async def execute_run(self, run_id: str, user_id: str):
        run_obj_id = ObjectId(run_id)
        user_obj_id = ObjectId(user_id)

        run = await run_repository.get_by_id(run_obj_id, user_obj_id)
        if not run:
            logger.error("Run not found", run_id=run_id)
            return

        # Fetch spec to get base_url and auth_config for execution context
        from app.db.repositories import spec_repository
        spec = await spec_repository.get_by_id(run.spec_id, user_obj_id)
        if spec:
            # Update run config with spec's base_url and auth_config if not overridden
            if not run.config.base_url_override and spec.base_url:
                run.config.spec_base_url = spec.base_url
            if not run.config.auth_override and spec.auth_config:
                run.config.spec_auth_config = spec.auth_config
            # Persist updated config
            await run_repository.update_config(run_obj_id, run.config)

        await run_repository.update_status(run_obj_id, "running")
        run = await run_repository.get_by_id(run_obj_id, user_obj_id)

        context = RunContext(run_obj_id, run.config)
        self.active_runs[run_id] = context

        executor = TestExecutor(
            max_concurrent_requests=run.config.concurrency,
            request_timeout=run.config.timeout_seconds,
            max_retries=run.config.retry_failed,
            rate_limit_rps=None,
        )

        try:
            test_cases = await test_case_repository.list_by_spec(
                run.spec_id,
                category=None,
                limit=10000,
            )

            filtered_cases = [tc for tc in test_cases if tc.category in run.config.categories]
            logger.info("Starting test execution", run_id=run_id, total_cases=len(filtered_cases))

            tasks = []
            for tc in filtered_cases:
                if context.is_cancelled():
                    break
                task = asyncio.create_task(self._execute_single(executor, context, tc))
                context.add_task(str(tc.id), task)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            passed = failed = errors = skipped = 0
            result_docs = []

            for i, result in enumerate(results):
                tc = filtered_cases[i]
                context.remove_task(str(tc.id))

                if isinstance(result, Exception):
                    logger.error("Test execution exception", test_case_id=str(tc.id), error=str(result))
                    errors += 1
                    result_doc = TestResultBase(
                        run_id=run_obj_id,
                        test_case_id=tc.id,
                        endpoint_id=tc.endpoint_id,
                        category=tc.category,
                        status="error",
                        request_sent=RequestSent(
                            method=tc.request.method,
                            url=tc.request.path,
                            headers=tc.request.headers,
                            body=tc.request.body,
                        ),
                        response=ResponseReceived(
                            status_code=0,
                            headers={},
                            body=None,
                            duration_ms=0,
                        ),
                        error=str(result),
                    )
                else:
                    result_doc = result
                    if result.status == "passed":
                        passed += 1
                    elif result.status == "failed":
                        failed += 1
                    elif result.status == "error":
                        errors += 1
                    elif result.status == "skipped":
                        skipped += 1

                result_docs.append(result_doc)

            if result_docs:
                await result_repository.bulk_create(result_docs)

            await run_repository.increment_summary(run_obj_id, "total", len(filtered_cases))
            await run_repository.increment_summary(run_obj_id, "passed", passed)
            await run_repository.increment_summary(run_obj_id, "failed", failed)
            await run_repository.increment_summary(run_obj_id, "errors", errors)
            await run_repository.increment_summary(run_obj_id, "skipped", skipped)

            final_status = "cancelled" if context.is_cancelled() else ("completed" if errors == 0 else "completed")
            await run_repository.update_status(run_obj_id, final_status)

            logger.info("Run completed", run_id=run_id, passed=passed, failed=failed, errors=errors, skipped=skipped)

        except Exception as e:
            logger.exception("Run execution failed", run_id=run_id, error=str(e))
            await run_repository.update_status(run_obj_id, "failed")
        finally:
            await executor.close()
            self.active_runs.pop(run_id, None)

    async def _execute_single(self, executor: TestExecutor, context: RunContext, test_case: TestCaseInDB):
        return await executor.execute_test_case(test_case, context)

    async def cancel_run(self, run_id: ObjectId):
        run_id_str = str(run_id)
        context = self.active_runs.get(run_id_str)
        if context:
            await context.cancel_all()
            await run_repository.update_status(run_id, "cancelling")

    async def retry_failed(self, run_id: ObjectId):
        failed_results = await result_repository.list_by_run(run_id, status="failed")
        error_results = await result_repository.list_by_run(run_id, status="error")

        all_failed = failed_results + error_results
        if not all_failed:
            return

        run_doc = await run_repository.collection.find_one({"_id": run_id})
        if not run_doc:
            return

        await run_repository.update_status(run_id, "running")

        test_case_ids = [r.test_case_id for r in all_failed]

        test_cases = []
        for tc_id in test_case_ids:
            tc = await test_case_repository.get_by_id(tc_id)
            if tc:
                test_cases.append(tc)

        run_config = RunConfig(**run_doc.get("config", {}))

        executor = TestExecutor(
            max_concurrent_requests=run_config.concurrency,
            request_timeout=run_config.timeout_seconds,
            max_retries=run_config.retry_failed,
        )

        context = RunContext(run_id, run_config)
        self.active_runs[str(run_id)] = context

        try:
            tasks = []
            for tc in test_cases:
                if context.is_cancelled():
                    break
                task = asyncio.create_task(self._execute_single(executor, context, tc))
                context.add_task(str(tc.id), task)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for i, result in enumerate(results):
                tc = test_cases[i]
                context.remove_task(str(tc.id))
                existing_res = all_failed[i]

                if isinstance(result, Exception):
                    continue

                await result_repository.update_status(existing_res.id, result.status)
                if result.llm_analysis:
                    await result_repository.update_analysis(existing_res.id, result.llm_analysis.model_dump())

            await run_repository.update_status(run_id, "completed")

        finally:
            await executor.close()
            self.active_runs.pop(str(run_id), None)
