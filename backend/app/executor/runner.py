import asyncio
from datetime import UTC, datetime

import structlog
from bson import ObjectId

from app.config import get_settings
from app.db.models import AuthConfig, RunConfig, RunSummary, TestCaseInDB
from app.db.repositories import result_repository, run_repository, test_case_repository
from app.executor.engine import TestExecutor

logger = structlog.get_logger()

OWASP_API_TOP_10 = {
    "API1:2023": "Broken Object Level Authorization",
    "API2:2023": "Broken Authentication",
    "API3:2023": "Broken Object Property Level Authorization",
    "API4:2023": "Unrestricted Resource Consumption",
    "API5:2023": "Broken Function Level Authorization",
    "API6:2023": "Unrestricted Access to Sensitive Business Flows",
    "API7:2023": "Server Side Request Forgery",
    "API8:2023": "Security Misconfiguration",
    "API9:2023": "Improper Inventory Management",
    "API10:2023": "Unsafe Consumption of APIs",
}


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

    async def execute_run(self, run_id: str, user_id: str, *, cancel_token=None, progress_callback=None):
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

        # Session credentials are encrypted at rest and never placed in the
        # public run document. Resolve them only in this worker immediately
        # before execution.
        if run.config.auth_secret_ref:
            from app.core.security import decrypt_value
            from app.db.mongo import get_collection

            try:
                session = await get_collection("sessions").find_one(
                    {"_id": ObjectId(run.config.auth_secret_ref), "user_id": user_obj_id}
                )
                if session and session.get("auth_token_encrypted") and session.get("auth_type"):
                    run.config.auth_override = AuthConfig(
                        type=session["auth_type"], token=decrypt_value(session["auth_token_encrypted"])
                    )
                if session and session.get("secondary_auth_token_encrypted") and session.get("secondary_auth_type"):
                    run.config.auth_secondary = AuthConfig(
                        type=session["secondary_auth_type"], token=decrypt_value(session["secondary_auth_token_encrypted"])
                    )
            except Exception as exc:
                logger.error("Unable to resolve encrypted session credentials", error=type(exc).__name__)
                await run_repository.update_status(run_obj_id, "failed")
                return

        await run_repository.update_status(run_obj_id, "running")
        await run_repository.update_started_at(run_obj_id)
        run = await run_repository.get_by_id(run_obj_id, user_obj_id)

        # Server-enforce mode limits (cannot be overridden by client)
        if run.config.mode == "online":
            run.config.concurrency = min(run.config.concurrency, 3)
            if not run.config.rate_limit_rps or run.config.rate_limit_rps > 2.0:
                run.config.rate_limit_rps = 2.0
            if not run.config.owned_host_attestation:
                run.config.categories = [
                    c for c in run.config.categories if c not in ("security", "resource_consumption")
                ]

        context = RunContext(run_obj_id, run.config)
        self.active_runs[run_id] = context

        executor = TestExecutor(
            max_concurrent_requests=run.config.concurrency,
            request_timeout=run.config.timeout_seconds,
            max_retries=run.config.retry_failed,
            rate_limit_rps=run.config.rate_limit_rps,
            max_response_body_bytes=get_settings().max_response_body_bytes,
        )

        try:
            test_cases = (
                await test_case_repository.list_by_session(run.config.session_id, limit=10000)
                if run.config.session_id
                else await test_case_repository.list_by_spec(run.spec_id, category=None, limit=10000)
            )

            scoped_ids = set(run.config.test_case_ids or [])
            filtered_cases = [
                tc for tc in test_cases
                if tc.category in run.config.categories and (not scoped_ids or str(tc.id) in scoped_ids)
            ]
            selected_cases = list(filtered_cases)
            # A resumed run reuses durable results and dispatches only cases that
            # have not already produced a result.
            existing = await result_repository.list_by_run(run_obj_id, limit=10000)
            completed_case_ids = {str(result.test_case_id) for result in existing}
            filtered_cases = [tc for tc in filtered_cases if str(tc.id) not in completed_case_ids]
            if len(filtered_cases) > run.config.max_total_requests:
                # Preserve category coverage when enforcing the request budget.
                by_category = {category: [] for category in run.config.categories}
                for tc in filtered_cases:
                    by_category.setdefault(tc.category, []).append(tc)
                balanced = []
                while len(balanced) < run.config.max_total_requests and any(by_category.values()):
                    for category in run.config.categories:
                        bucket = by_category.get(category, [])
                        if bucket and len(balanced) < run.config.max_total_requests:
                            balanced.append(bucket.pop(0))
                filtered_cases = balanced
                logger.warning(
                    "Run request budget enforced",
                    run_id=run_id,
                    max_total_requests=run.config.max_total_requests,
                )
            selected_count = len(filtered_cases) + len(completed_case_ids)
            logger.info("Starting test execution", run_id=run_id, selected_cases=selected_count, dispatch_count=len(filtered_cases))

            tasks = []
            for tc in filtered_cases:
                if context.is_cancelled() or (cancel_token and await cancel_token.cancelled()):
                    await context.cancel_all()
                    break
                task = asyncio.create_task(self._execute_single(executor, context, tc))
                context.add_task(str(tc.id), task)
                tasks.append(task)

            passed = failed = errors = skipped = blocked = 0
            executed_count = persistence_errors = 0
            last_persistence_error = None

            for task in asyncio.as_completed(tasks):
                if context.is_cancelled() or (cancel_token and await cancel_token.cancelled()):
                    await context.cancel_all()
                    break
                try:
                    result = await task
                    context.remove_task(str(result.test_case_id))
                    executed_count += 1

                    # Persist each result immediately
                    try:
                        persisted = await result_repository.create(result)
                        logger.info(
                            "Execution result persisted",
                            run_id=run_id,
                            test_case_id=str(result.test_case_id),
                            outcome=result.status,
                            database=get_settings().mongodb_db,
                            collection="test_results",
                            result_id=str(persisted.id),
                        )
                    except Exception as exc:
                        persistence_errors += 1
                        last_persistence_error = type(exc).__name__
                        logger.exception(
                            "Execution result persistence failed",
                            run_id=run_id,
                            test_case_id=str(result.test_case_id),
                            outcome=result.status,
                            database=get_settings().mongodb_db,
                            collection="test_results",
                            error_type=type(exc).__name__,
                        )
                        continue

                    # Update summary counters atomically
                    if result.status == "passed":
                        passed += 1
                        await run_repository.increment_summary(run_obj_id, "passed", 1)
                    elif result.status == "failed":
                        failed += 1
                        await run_repository.increment_summary(run_obj_id, "failed", 1)
                    elif result.status == "error":
                        errors += 1
                        await run_repository.increment_summary(run_obj_id, "errors", 1)
                    elif result.status == "skipped":
                        skipped += 1
                        await run_repository.increment_summary(run_obj_id, "skipped", 1)
                    elif result.status == "blocked":
                        blocked += 1
                        await run_repository.increment_summary(run_obj_id, "blocked", 1)
                    if progress_callback:
                        await progress_callback(executed_count, len(filtered_cases), {"passed": passed, "failed": failed, "errors": errors, "skipped": skipped, "blocked": blocked})

                except Exception as e:
                    logger.error("Test execution exception", error=str(e))
                    errors += 1
                    await run_repository.increment_summary(run_obj_id, "errors", 1)

            persisted_results = await result_repository.list_by_run(run_obj_id, limit=10000)
            persisted_count = len(persisted_results)
            reconciled = RunSummary(
                total=persisted_count,
                passed=sum(r.status == "passed" for r in persisted_results),
                failed=sum(r.status == "failed" for r in persisted_results),
                errors=sum(r.status == "error" for r in persisted_results),
                skipped=sum(r.status == "skipped" for r in persisted_results),
                blocked=sum(r.status == "blocked" for r in persisted_results),
            )
            completed_at = datetime.now(UTC)
            run_after_execution = await run_repository.get_by_id(run_obj_id, user_obj_id)
            if run_after_execution and run_after_execution.started_at:
                reconciled.duration_seconds = max(0.0, (completed_at - run_after_execution.started_at).total_seconds())
            await run_repository.replace_summary(run_obj_id, reconciled)
            await run_repository.reconcile_results(
                run_obj_id,
                selected_count=selected_count,
                executed_count=executed_count + len(completed_case_ids),
                persisted_count=persisted_count,
                summary_count=reconciled.total,
                insertion_errors=persistence_errors,
                last_error=last_persistence_error,
            )
            coverage = []
            for category_id, category_name in OWASP_API_TOP_10.items():
                applicable = [case for case in selected_cases if case.metadata.owasp_category == category_id]
                applicable_ids = {str(case.id) for case in applicable}
                executed = [result for result in persisted_results if str(result.test_case_id) in applicable_ids]
                if not applicable:
                    assessment = "not_assessed"
                    reason = "No applicable generated security test case in this run scope."
                elif not executed:
                    assessment = "not_assessed"
                    reason = "Applicable tests were not persisted after execution."
                elif all(result.status == "blocked" for result in executed):
                    assessment = "blocked_by_execution_policy"
                    reason = "All applicable tests were blocked by execution policy."
                elif len(executed) < len(applicable):
                    assessment = "partially_assessed"
                    reason = "Only a subset of applicable tests produced persisted evidence."
                else:
                    assessment = "assessed"
                    reason = None
                coverage.append({
                    "id": category_id, "name": category_name, "assessment": assessment,
                    "applicable_endpoints": sorted({case.endpoint_id for case in applicable}),
                    "generated_test_cases": len(applicable), "executed_test_cases": len(executed),
                    "passed_checks": sum(result.status == "passed" for result in executed),
                    "failed_checks": sum(result.status == "failed" for result in executed),
                    "blocked_checks": sum(result.status == "blocked" for result in executed),
                    "not_assessed_reason": reason,
                    "evidence_result_ids": [str(result.id) for result in executed],
                })
            await run_repository.collection.update_one({"_id": run_obj_id}, {"$set": {"owasp_coverage": coverage}})
            logger.info("Execution reconciliation", run_id=run_id, selected=selected_count, executed=executed_count + len(completed_case_ids), persisted=persisted_count, summary=reconciled.total, persistence_errors=persistence_errors, database=get_settings().mongodb_db, collection="test_results")

            final_status = (
                "cancelled" if context.is_cancelled() or (cancel_token and await cancel_token.cancelled()) else ("completed_with_errors" if errors > 0 or persistence_errors > 0 else "completed")
            )
            await run_repository.update_status(run_obj_id, final_status)
            await run_repository.update_completed_at(run_obj_id)

            logger.info(
                "Run completed",
                run_id=run_id,
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                blocked=blocked,
                persisted=persisted_count,
                persistence_errors=persistence_errors,
            )

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

            retry_write_errors = 0
            for task in asyncio.as_completed(tasks):
                try:
                    result = await task
                    existing_res = next(r for r in all_failed if r.test_case_id == result.test_case_id)

                    replaced = await result_repository.replace_execution(
                        existing_res.id, result, attempt=existing_res.attempt + 1
                    )
                    if not replaced:
                        retry_write_errors += 1
                        logger.error("Retry result was not persisted", result_id=str(existing_res.id))
                except Exception as e:
                    retry_write_errors += 1
                    logger.exception("Retry execution exception", run_id=str(run_id), error_type=type(e).__name__)

            persisted_results = await result_repository.list_by_run(run_id, limit=10000)
            summary = RunSummary(
                total=len(persisted_results),
                passed=sum(result.status == "passed" for result in persisted_results),
                failed=sum(result.status == "failed" for result in persisted_results),
                errors=sum(result.status == "error" for result in persisted_results),
                skipped=sum(result.status == "skipped" for result in persisted_results),
                blocked=sum(result.status == "blocked" for result in persisted_results),
            )
            await run_repository.replace_summary(run_id, summary)
            await run_repository.reconcile_results(
                run_id,
                selected_count=summary.total,
                executed_count=summary.total,
                persisted_count=summary.total,
                summary_count=summary.total,
                insertion_errors=retry_write_errors,
                last_error="retry persistence failure" if retry_write_errors else None,
            )
            await run_repository.update_status(
                run_id, "completed_with_errors" if summary.errors or retry_write_errors else "completed"
            )

        finally:
            await executor.close()
            self.active_runs.pop(str(run_id), None)
