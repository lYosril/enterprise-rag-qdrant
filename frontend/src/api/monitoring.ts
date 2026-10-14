import { api } from './client'
import type { MonitoringStats } from '../types'

export async function getMonitoringStats(): Promise<MonitoringStats> {
  const response = await api.get<MonitoringStats>('/api/v1/monitoring/stats')
  return response.data
}
