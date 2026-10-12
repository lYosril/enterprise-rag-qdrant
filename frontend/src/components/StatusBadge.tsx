import { CheckCircle, Clock, XCircle } from 'lucide-react'
import Spinner from './Spinner'

interface StatusBadgeProps {
  status: string
}

const CONFIG: Record<
  string,
  { label: string; classes: string; icon: React.ReactNode }
> = {
  uploaded: {
    label: 'Uploaded',
    classes: 'bg-gray-100 text-gray-600',
    icon: <Clock size={12} />,
  },
  processing: {
    label: 'Processing',
    classes: 'bg-yellow-100 text-yellow-700',
    icon: <Spinner size={12} className="text-yellow-600" />,
  },
  indexed: {
    label: 'Indexed',
    classes: 'bg-brand-light text-brand-dark',
    icon: <CheckCircle size={12} />,
  },
  failed: {
    label: 'Failed',
    classes: 'bg-red-100 text-red-600',
    icon: <XCircle size={12} />,
  },
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const cfg = CONFIG[status] ?? {
    label: status,
    classes: 'bg-gray-100 text-gray-500',
    icon: null,
  }

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.classes}`}
    >
      {cfg.icon}
      {cfg.label}
    </span>
  )
}
