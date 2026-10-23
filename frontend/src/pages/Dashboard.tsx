import { useQuery } from '@tanstack/react-query'
import { specsApi, runsApi } from '../api/endpoints'
import { Card, CardHeader, CardTitle, CardContent, CardDescription } from '../components/ui/Card'
import { StatusBadge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Database, PlayCircle, FileText, Clock } from '@phosphor-icons/react'
import { clsx } from 'clsx'
import { formatDistanceToNow } from 'date-fns'
import { Link } from 'react-router-dom'

export function Dashboard() {
  const { data: specsData } = useQuery({
    queryKey: ['specs', 1, 5],
    queryFn: () => specsApi.list({ page: 1, page_size: 5 }),
  })

  const { data: runsData } = useQuery({
    queryKey: ['runs', 1, 5],
    queryFn: () => runsApi.list({ page: 1, page_size: 5 }),
  })

  const stats = [
    { label: 'API Specs', value: specsData?.data.total || 0, icon: Database, color: 'text-brand-600 bg-brand-100 dark:bg-brand-900/30', href: '/specs' },
    { label: 'Test Runs', value: runsData?.data.total || 0, icon: PlayCircle, color: 'text-green-600 bg-green-100 dark:bg-green-900/30', href: '/runs' },
    { label: 'Reports', value: 0, icon: FileText, color: 'text-purple-600 bg-purple-100 dark:bg-purple-900/30', href: '/reports' },
    { label: 'Active Runs', value: runsData?.data.runs.filter(r => r.status === 'running').length || 0, icon: Clock, color: 'text-orange-600 bg-orange-100 dark:bg-orange-900/30', href: '/runs?status=running' },
  ]

  const recentRuns = runsData?.data.runs || []
  const recentSpecs = specsData?.data.specs || []

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-50">Dashboard</h1>
          <p className="text-zinc-500 dark:text-zinc-400 mt-1">Overview of your API testing activity</p>
        </div>
        <Link to="/specs/upload">
          <Button>
            <PlayCircle className="h-4 w-4" />
            New Test Run
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Link key={stat.label} to={stat.href} className="card-hover">
              <Card padding="md">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-zinc-500 dark:text-zinc-400">{stat.label}</p>
                    <p className="text-3xl font-bold text-zinc-900 dark:text-zinc-50 mt-1">{stat.value}</p>
                  </div>
                  <div className={clsx('w-12 h-12 rounded-12 flex items-center justify-center', stat.color)}>
                    <Icon className="h-6 w-6" />
                  </div>
                </div>
              </Card>
            </Link>
          )
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Recent Test Runs</CardTitle>
            <CardDescription>Latest test executions</CardDescription>
          </CardHeader>
          <CardContent>
            {recentRuns.length === 0 ? (
              <div className="text-center py-8">
                <PlayCircle className="h-12 w-12 text-zinc-300 dark:text-zinc-600 mx-auto mb-3" />
                <p className="text-zinc-500 dark:text-zinc-400">No test runs yet</p>
                <Link to="/specs/upload" className="mt-3 inline-block">
                  <Button size="sm">Create Your First Run</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {recentRuns.map((run) => (
                  <Link key={run.id} to={`/runs/${run.id}`} className="flex items-center justify-between p-3 rounded-10 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className={clsx('w-8 h-8 rounded-10 flex items-center justify-center', 
                        run.status === 'completed' ? 'bg-green-100 dark:bg-green-900/30' :
                        run.status === 'running' ? 'bg-blue-100 dark:bg-blue-900/30' :
                        run.status === 'failed' ? 'bg-red-100 dark:bg-red-900/30' :
                        'bg-zinc-100 dark:bg-zinc-800'
                      )}>
                        <PlayCircle className={clsx('h-4 w-4',
                          run.status === 'completed' ? 'text-green-600' :
                          run.status === 'running' ? 'text-blue-600 animate-spin' :
                          run.status === 'failed' ? 'text-red-600' :
                          'text-zinc-600'
                        )} />
                      </div>
                      <div>
                        <p className="font-medium text-zinc-900 dark:text-zinc-50 truncate max-w-[200px]">{run.name}</p>
                        <p className="text-xs text-zinc-500 dark:text-zinc-400">{formatDistanceToNow(new Date(run.created_at), { addSuffix: true })}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge status={run.status} />
                      <span className="text-sm text-zinc-500 dark:text-zinc-400">
                        {run.summary.passed}/{run.summary.total}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent Specifications</CardTitle>
            <CardDescription>Your uploaded API specs</CardDescription>
          </CardHeader>
          <CardContent>
            {recentSpecs.length === 0 ? (
              <div className="text-center py-8">
                <Database className="h-12 w-12 text-zinc-300 dark:text-zinc-600 mx-auto mb-3" />
                <p className="text-zinc-500 dark:text-zinc-400">No specifications uploaded</p>
                <Link to="/specs/upload" className="mt-3 inline-block">
                  <Button size="sm">Upload Your First Spec</Button>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {recentSpecs.map((spec) => (
                  <Link key={spec.id} to={`/specs/${spec.id}`} className="flex items-center justify-between p-3 rounded-10 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <div className={clsx('w-8 h-8 rounded-10 flex items-center justify-center',
                        spec.status === 'ready' ? 'bg-green-100 dark:bg-green-900/30' :
                        spec.status === 'parsing' ? 'bg-blue-100 dark:bg-blue-900/30' :
                        'bg-red-100 dark:bg-red-900/30'
                      )}>
                        <Database className={clsx('h-4 w-4',
                          spec.status === 'ready' ? 'text-green-600' :
                          spec.status === 'parsing' ? 'text-blue-600 animate-spin' :
                          'text-red-600'
                        )} />
                      </div>
                      <div>
                        <p className="font-medium text-zinc-900 dark:text-zinc-50 truncate max-w-[200px]">{spec.name}</p>
                        <p className="text-xs text-zinc-500 dark:text-zinc-400">{spec.endpoints_count} endpoints • {formatDistanceToNow(new Date(spec.created_at), { addSuffix: true })}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusBadge status={spec.status} />
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}