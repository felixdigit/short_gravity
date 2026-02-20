import { useQuery } from '@tanstack/react-query'

export interface FeedItem {
  id: string
  type: 'sec' | 'fcc' | 'pr' | 'call' | 'x' | 'signal'
  title: string
  date: string
  url: string | null
  badge: string | null
}

export interface ActivityFeedResponse {
  items: FeedItem[]
}

export function useActivityFeed() {
  return useQuery<ActivityFeedResponse>({
    queryKey: ['activity-feed'],
    queryFn: async () => {
      const res = await fetch('/api/widgets/activity-feed')
      if (!res.ok) throw new Error('Failed to fetch activity feed')
      return res.json()
    },
    staleTime: 15 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000,
  })
}
