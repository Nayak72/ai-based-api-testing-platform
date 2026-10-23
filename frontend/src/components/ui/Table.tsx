import { HTMLAttributes, ReactNode } from 'react'
import { clsx } from 'clsx'
import { CaretUp, CaretDown, CaretLeft, CaretRight, CaretDoubleLeft, CaretDoubleRight, Spinner } from '@phosphor-icons/react'

export interface Column<T> {
  key: string
  header: string
  render?: (row: T, index: number) => ReactNode
  className?: string
  sortable?: boolean
  width?: string
}

export interface TableProps<T> extends Omit<HTMLAttributes<HTMLTableElement>, 'children'> {
  columns: Column<T>[]
  data: T[]
  keyExtractor: (row: T) => string
  onRowClick?: (row: T) => void
  sortColumn?: string
  sortDirection?: 'asc' | 'desc'
  onSort?: (column: string) => void
  loading?: boolean
  emptyMessage?: string
  striped?: boolean
  hoverable?: boolean
  children?: ((props: { row: T; index: number }) => ReactNode) | ReactNode
}

export function Table<T>({
  columns,
  data,
  keyExtractor,
  onRowClick,
  sortColumn,
  sortDirection,
  onSort,
  loading,
  emptyMessage = 'No data available',
  striped = true,
  hoverable = true,
  className,
  children,
  ...props
}: TableProps<T>) {
  const handleSort = (columnKey: string) => {
    const column = columns.find(c => c.key === columnKey)
    if (column?.sortable && onSort) {
      onSort(columnKey)
    }
  }

  const renderSortIcon = (columnKey: string) => {
    if (sortColumn !== columnKey) return null
    return sortDirection === 'asc' ? <CaretUp className="h-4 w-4" /> : <CaretDown className="h-4 w-4" />
  }

  if (loading) {
    return (
      <div className={clsx("table-container", className)} {...props}>
        <table className="table" role="table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} className={clsx(column.className)} style={{ width: column.width }}>
                  <div className="flex items-center gap-1">
                    {column.header}
                    {column.sortable && (
                      <span className="text-zinc-300 dark:text-zinc-600">
                        <CaretUp className="h-3 w-3" />
                        <CaretDown className="h-3 w-3" />
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={columns.length} className="px-4 py-8 text-center">
                <div className="flex flex-col items-center gap-3">
                  <Spinner className="animate-spin h-8 w-8 text-brand-500" />
                  <p className="text-zinc-500 dark:text-zinc-400">Loading...</p>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className={clsx("table-container", className)} {...props}>
        <table className="table" role="table">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.key} className={clsx(column.className)} style={{ width: column.width }}>
                  <div className="flex items-center gap-1">
                    {column.header}
                    {column.sortable && (
                      <span className="text-zinc-300 dark:text-zinc-600">
                        <CaretUp className="h-3 w-3" />
                        <CaretDown className="h-3 w-3" />
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={columns.length} className="px-4 py-12 text-center">
                <p className="text-zinc-500 dark:text-zinc-400">{emptyMessage}</p>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    )
  }

  return (
    <div className={clsx("table-container", className)} {...props}>
      <table className="table" role="table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                className={clsx(
                  column.className,
                  column.sortable && 'cursor-pointer select-none hover:bg-zinc-100 dark:hover:bg-zinc-800'
                )}
                style={{ width: column.width }}
                onClick={() => handleSort(column.key)}
              >
                <div className="flex items-center gap-1">
                  {column.header}
                  {column.sortable && renderSortIcon(column.key)}
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, rowIndex) => (
            <tr
              key={keyExtractor(row)}
              className={clsx(
                striped && rowIndex % 2 === 1 && 'bg-zinc-50 dark:bg-zinc-800/30',
                hoverable && onRowClick && 'cursor-pointer'
              )}
              onClick={() => onRowClick?.(row)}
            >
              {typeof children === 'function'
                ? (children as (props: { row: T; index: number }) => ReactNode)({ row, index: rowIndex })
                : columns.map((column) => (
                    <td key={column.key} className={clsx(column.className)}>
                      {column.render ? column.render(row, rowIndex) : (row as any)[column.key]}
                    </td>
                  ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function Pagination({
  currentPage,
  totalPages,
  onPageChange,
  pageSize,
  totalItems,
  showPageSize = false,
  pageSizeOptions = [10, 20, 50, 100],
}: {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
  pageSize?: number
  totalItems?: number
  showPageSize?: boolean
  pageSizeOptions?: number[]
}) {
  if (totalPages <= 1) return null

  const pages = []
  const maxVisiblePages = 5
  let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2))
  let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1)

  if (endPage - startPage + 1 < maxVisiblePages) {
    startPage = Math.max(1, endPage - maxVisiblePages + 1)
  }

  for (let i = startPage; i <= endPage; i++) {
    pages.push(i)
  }

  return (
    <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mt-4 px-4 pb-4">
      <div className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
        {totalItems !== undefined && (
          <span>
            Showing {(currentPage - 1) * (pageSize || 10) + 1} to {Math.min(currentPage * (pageSize || 10), totalItems)} of {totalItems} results
          </span>
        )}
        {showPageSize && pageSize && (
          <select
            value={pageSize}
            onChange={() => onPageChange(1)}
            className="input w-auto py-1 px-2 text-xs"
            onKeyDown={(e) => e.stopPropagation()}
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size} per page
              </option>
            ))}
          </select>
        )}
      </div>

      <nav className="flex items-center gap-1" aria-label="Pagination">
        <button
          onClick={() => onPageChange(1)}
          disabled={currentPage === 1}
          className="btn-ghost p-1.5 disabled:opacity-30"
          aria-label="First page"
        >
          <CaretDoubleLeft className="h-4 w-4" />
        </button>
        <button
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage === 1}
          className="btn-ghost p-1.5 disabled:opacity-30"
          aria-label="Previous page"
        >
          <CaretLeft className="h-4 w-4" />
        </button>

        {startPage > 1 && (
          <>
            <button onClick={() => onPageChange(1)} className="btn-ghost px-3 py-1.5">
              1
            </button>
            {startPage > 2 && <span className="px-2 text-zinc-400">...</span>}
          </>
        )}

        {pages.map((page) => (
          <button
            key={page}
            onClick={() => onPageChange(page)}
            className={clsx(
              'btn-ghost px-3 py-1.5 min-w-[2.5rem]',
              currentPage === page && 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300'
            )}
            aria-current={currentPage === page ? 'page' : undefined}
          >
            {page}
          </button>
        ))}

        {endPage < totalPages && (
          <>
            {endPage < totalPages - 1 && <span className="px-2 text-zinc-400">...</span>}
            <button onClick={() => onPageChange(totalPages)} className="btn-ghost px-3 py-1.5">
              {totalPages}
            </button>
          </>
        )}

        <button
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage === totalPages}
          className="btn-ghost p-1.5 disabled:opacity-30"
          aria-label="Next page"
        >
          <CaretRight className="h-4 w-4" />
        </button>
        <button
          onClick={() => onPageChange(totalPages)}
          disabled={currentPage === totalPages}
          className="btn-ghost p-1.5 disabled:opacity-30"
          aria-label="Last page"
        >
          <CaretDoubleRight className="h-4 w-4" />
        </button>
      </nav>
    </div>
  )
}