/**
 * Earnings Guidance Ledger — Static Data
 *
 * Management promises tracked against outcomes.
 * Manually curated — fewer than 15 critical items.
 * Used by: /earnings page, Guidance Ledger component.
 */

export type GuidanceStatus = 'PENDING' | 'MET' | 'MISSED' | 'DELAYED' | 'DROPPED'
export type GuidanceCategory = 'LAUNCH' | 'FINANCIAL' | 'COMMERCIAL' | 'REGULATORY'

export interface GuidanceItem {
  id: string
  /** Quarter when promise was made */
  quarter_promised: string
  /** Quarter when outcome is expected/due */
  quarter_due: string
  category: GuidanceCategory
  promise_text: string
  outcome_text?: string
  status: GuidanceStatus
  /** URL to source filing, press release, or transcript */
  source_url?: string
}

export const GUIDANCE_ITEMS: GuidanceItem[] = [
  {
    id: 'bw3-launch',
    quarter_promised: '2022-Q4',
    quarter_due: '2023-Q2',
    category: 'LAUNCH',
    promise_text: 'Launch BlueWalker 3 test satellite',
    outcome_text: 'BW3 launched April 2023. Unfolded largest commercial array in space (64 sqm).',
    status: 'MET',
  },
  {
    id: 'bb-5-launch',
    quarter_promised: '2023-Q4',
    quarter_due: '2024-Q3',
    category: 'LAUNCH',
    promise_text: 'Launch first 5 BlueBird Block 1 satellites by September 2024',
    outcome_text: 'BB1-5 launched September 12, 2024 via SpaceX Falcon 9.',
    status: 'MET',
  },
  {
    id: 'funded-through-commercial',
    quarter_promised: '2024-Q1',
    quarter_due: '2025-Q2',
    category: 'FINANCIAL',
    promise_text: 'Company funded through initial commercial service launch',
    outcome_text: 'Confirmed via ATM facility ($500M shelf) + existing cash. Multiple capital raises completed.',
    status: 'MET',
  },
  {
    id: 'first-commercial-service',
    quarter_promised: '2024-Q2',
    quarter_due: '2025-Q2',
    category: 'COMMERCIAL',
    promise_text: 'Begin initial commercial service in 2025',
    status: 'PENDING',
  },
  {
    id: 'fm1-unfold',
    quarter_promised: '2024-Q3',
    quarter_due: '2025-Q1',
    category: 'LAUNCH',
    promise_text: 'Unfold FM1 (first BlueBird) array on orbit',
    status: 'PENDING',
  },
  {
    id: 'scs-license',
    quarter_promised: '2024-Q3',
    quarter_due: '2025-Q2',
    category: 'REGULATORY',
    promise_text: 'Obtain FCC Supplemental Coverage from Space (SCS) license',
    outcome_text: 'Application filed (Docket 25-201). Under review.',
    status: 'PENDING',
  },
  {
    id: 'att-partnership-launch',
    quarter_promised: '2024-Q2',
    quarter_due: '2025-Q2',
    category: 'COMMERCIAL',
    promise_text: 'Launch commercial service with AT&T as first US carrier partner',
    status: 'PENDING',
  },
  {
    id: '50-mno-agreements',
    quarter_promised: '2023-Q3',
    quarter_due: '2024-Q4',
    category: 'COMMERCIAL',
    promise_text: 'Secure 50+ MNO agreements covering 2.8B subscribers',
    outcome_text: 'Over 50 MNO agreements signed as of Q4 2024.',
    status: 'MET',
  },
  {
    id: 'block2-production',
    quarter_promised: '2024-Q4',
    quarter_due: '2026-Q2',
    category: 'LAUNCH',
    promise_text: 'Begin Block 2 satellite production at Midland facility',
    status: 'PENDING',
  },
  {
    id: 'continuous-coverage',
    quarter_promised: '2024-Q3',
    quarter_due: '2027-Q4',
    category: 'COMMERCIAL',
    promise_text: 'Achieve continuous global coverage with full constellation (~168 satellites)',
    status: 'PENDING',
  },
]
