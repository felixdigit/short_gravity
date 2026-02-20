-- Migration 023: Catalysts table
-- Replaces hardcoded lib/data/catalysts.ts with queryable database
-- Part of Thread 002: Event Horizon

CREATE TABLE IF NOT EXISTS catalysts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title TEXT NOT NULL,
  description TEXT,
  category TEXT NOT NULL,  -- launch, commercial, regulatory, government, funding, spectrum, technical, revenue, coverage, investment, production, team, ip, index

  -- Temporal: at least one should be set for upcoming catalysts
  event_date DATE,              -- Precise date (if known)
  estimated_period TEXT,         -- Fuzzy: 'Q1 2026', 'H2 2026', '2026', 'FEB 2026'

  -- Status
  status TEXT NOT NULL DEFAULT 'upcoming',  -- upcoming, completed
  completed_date DATE,           -- When it actually happened (for completed items)

  -- Source linking (reuses Thread 001 infrastructure)
  source_url TEXT,

  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- RLS
ALTER TABLE catalysts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "catalysts_public_read" ON catalysts FOR SELECT USING (true);

-- Index for horizon queries
CREATE INDEX idx_catalysts_status_date ON catalysts (status, event_date) WHERE status = 'upcoming';
CREATE INDEX idx_catalysts_category ON catalysts (category);

-- ============================================================================
-- Seed: Upcoming catalysts (migrated from lib/data/catalysts.ts)
-- Dates estimated from SEC filings, press releases, and FCC docket timelines
-- ============================================================================

INSERT INTO catalysts (title, description, category, event_date, estimated_period, status) VALUES
  ('FM2 Delivery to Florida + Launch', 'Second Block-2 satellite for SpaceX launch from Cape Canaveral', 'launch', '2026-02-28', 'FEB 2026', 'upcoming'),
  ('FM3-5 Delivery + Launch', 'Batch of 3 Block-2 satellites for constellation buildout', 'launch', '2026-06-15', 'H1 2026', 'upcoming'),
  ('Block-2 Batch Launches (3-8x sats/1-2mo)', 'Continuous cadence of satellite deployments throughout 2026', 'launch', NULL, '2026', 'upcoming'),
  ('Verizon Definitive Commercial Agreement', 'Converting MOU to binding commercial terms with prepaid revenue', 'commercial', NULL, 'H1 2026', 'upcoming'),
  ('Bell Canada Definitive Agreement', 'Canadian market access, beta testing STA already granted', 'commercial', NULL, 'H1 2026', 'upcoming'),
  ('FirstNet Investment + Agreement', 'Public safety Band 14 evaluation ongoing per FCC STA', 'commercial', NULL, '2026', 'upcoming'),
  ('Golden Dome Award(s)', 'US government missile defense satellite communication contracts', 'government', NULL, '2026', 'upcoming'),
  ('Ligado Confirmation + FCC Approval', '45MHz L-Band spectrum, Docket 25-201 active. AT&T filed support Jan 2026', 'regulatory', NULL, 'Q1 2026', 'upcoming'),
  ('FCC Full US Commercial Service Approval', 'Application accepted, pending final authorization', 'regulatory', NULL, 'Q2 2026', 'upcoming'),
  ('AT&T/Vodafone/Verizon Milestone Prepayments ($110M)', '$20M/$25M/$65M unlocking upon service milestones', 'revenue', NULL, 'H2 2026', 'upcoming'),
  ('Telefonica/Saudi Telecom Definitive Agreements', 'Converting MOUs from 50+ MNO partners to binding deals', 'commercial', NULL, '2026', 'upcoming'),
  ('AT&T/Verizon/Vodafone/Rakuten Beta Results', 'Beta testing STA granted, video calls already demonstrated', 'technical', NULL, 'Q1 2026', 'upcoming'),
  ('Google Services Partnership Update', 'Integration of Google services over satellite connectivity', 'commercial', NULL, '2026', 'upcoming'),
  ('Goldman/Morgan Stanley/Stifel Coverage', 'Major bank initiation to complement BofA/Clear Street/Roth', 'coverage', NULL, 'H1 2026', 'upcoming'),
  ('DoD/SDA/DIU Contract Expansion', 'Expand beyond $63M existing contracts with defense agencies', 'government', NULL, '2026', 'upcoming'),
  ('FCC 5G Fund Grant', 'Federal funding for rural broadband satellite deployment', 'regulatory', NULL, '2026', 'upcoming'),
  ('Strategic Investment (Apple/Amazon/MSFT/PIF?)', 'Potential anchor investment from tech/sovereign wealth', 'investment', NULL, '2026', 'upcoming'),
  ('PNT Service FCC Proposal (GPS Alt)', 'Position, Navigation, Timing service as GPS backup', 'regulatory', NULL, '2027', 'upcoming'),
  ('Commercial Service Launch (2026)', 'Initial non-continuous service in US, Europe, Japan markets', 'commercial', NULL, 'H2 2026', 'upcoming'),
  ('EXIM/IFC $500M+ Non-Dilutive Funding', 'Export-Import Bank and IFC development financing', 'funding', NULL, '2026', 'upcoming'),
  ('SiriusXM/Echostar Spectrum Deal', 'Additional spectrum sharing for expanded capacity', 'spectrum', NULL, '2026', 'upcoming'),
  ('L/S-Band Global Spectrum Licenses', 'ITU priority rights being converted to national licenses', 'spectrum', NULL, '2026-2027', 'upcoming');

-- ============================================================================
-- Seed: Completed catalysts (migrated from lib/data/catalysts.ts)
-- ============================================================================

INSERT INTO catalysts (title, description, category, status, completed_date, estimated_period) VALUES
  ('FM1 BlueBird-1 Launch (ISRO GSLV)', 'First Block-2 satellite launched from Sriharikota, India', 'launch', 'completed', '2025-12-17', 'DEC 2025'),
  ('FCC Grant: 20x Block-2 Deployment', 'Authorization to deploy first 20 commercial satellites', 'regulatory', 'completed', '2025-09-18', 'SEP 2025'),
  ('FCC STA: 25x BlueBird Earth Stations', 'Ground station authorization for satellite operations', 'regulatory', 'completed', '2025-08-15', 'AUG 2025'),
  ('ITU S-Band Global Priority Rights', 'International spectrum coordination priority secured', 'spectrum', 'completed', '2025-07-15', 'JUL 2025'),
  ('First VoLTE/SMS with Standard Phone (AT&T)', 'World''s first native voice call over satellite with unmodified smartphone', 'technical', 'completed', '2024-09-16', 'SEP 2024'),
  ('JR Wilson Hired (ex-AT&T VP)', 'Chief of Networks, former AT&T VP Tower Strategy', 'team', 'completed', '2025-03-15', 'MAR 2025'),
  ('$575M Convertible Note + $1.5B Cash', '2.375% notes with capped call at $120, pro forma $1.5B cash', 'funding', 'completed', '2025-05-19', 'MAY 2025'),
  ('$360M Note Repurchase', 'Retired most of $460M 4.25% convertible notes', 'funding', 'completed', '2025-06-15', 'JUN 2025'),
  ('FM-1 FCC STA Granted', 'Experimental license for first Block-2 satellite testing', 'regulatory', 'completed', '2025-11-10', 'NOV 2025'),
  ('$550M Ligado Term Loan', 'Non-recourse secured loan to fund Ligado spectrum acquisition', 'funding', 'completed', '2025-10-15', 'OCT 2025'),
  ('$100M Equipment Loan Facility', 'Trinity Capital equipment financing for production', 'funding', 'completed', '2025-07-15', 'JUL 2025'),
  ('Russell 1000 Index Inclusion', 'Moved from Russell 2000, enabling larger fund investment', 'index', 'completed', '2025-06-23', 'JUN 2025'),
  ('Tactical NTN Demo w/ Fairwinds', 'First tactical satellite connectivity with defense prime', 'government', 'completed', '2025-04-15', 'APR 2025'),
  ('Ligado 45MHz L-Band Acquisition', 'US/Canada L-Band spectrum covering critical frequencies', 'spectrum', 'completed', '2025-10-15', 'OCT 2025'),
  ('Vodafone Idea India Partnership', 'Latest MNO partner for India market coverage', 'commercial', 'completed', '2025-08-15', 'AUG 2025'),
  ('Jennifer Manner Hired (ex-NTIA/EchoStar)', 'SVP Regulatory Affairs, former NTIA Senior Advisor', 'team', 'completed', '2025-02-15', 'FEB 2025'),
  ('FCC US Commercial Application Accepted', 'Application for full commercial service under review', 'regulatory', 'completed', '2025-10-15', 'OCT 2025'),
  ('Verizon/AT&T Spectrum Leases Filed', 'Carrier spectrum lease agreements on file with FCC', 'regulatory', 'completed', '2025-09-15', 'SEP 2025'),
  ('Beta Testing STA (AT&T/VZ/VOD/Bell/Rakuten)', 'Authorized beta testing with 5 major carriers', 'regulatory', 'completed', '2025-11-10', 'NOV 2025'),
  ('FirstNet Band 14 Evaluation STA', 'Public safety network evaluation authorization', 'regulatory', 'completed', '2025-11-10', 'NOV 2025'),
  ('Vodafone SatCo JV (Luxembourg)', 'European market JV headquartered in Luxembourg', 'commercial', 'completed', '2025-01-15', 'JAN 2025'),
  ('SDA/DIU Contracts ($63M)', '$43M Space Dev Agency + $20M Defense Innovation Unit', 'government', 'completed', '2025-05-08', 'MAY 2025'),
  ('AST5000 ASIC Integration Complete', 'Custom chip now integrated into Block-2 production', 'technical', 'completed', '2025-09-15', 'SEP 2025'),
  ('Video Calls (AT&T/VZ/VOD/Rakuten)', 'Successfully demonstrated video over satellite connectivity', 'technical', 'completed', '2025-10-20', 'OCT 2025'),
  ('SpaceX/Blue Origin/ISRO Launch Deals', 'Multi-launch agreements with three providers', 'launch', 'completed', '2025-08-15', 'AUG 2025'),
  ('3,650 Patent Claims (1,650 Granted)', '36 patent families protecting core technology', 'ip', 'completed', '2025-11-15', 'NOV 2025'),
  ('BofA/Clear Street/Roth Coverage', 'Analyst coverage from 6 investment banks', 'coverage', 'completed', '2025-06-15', 'JUN 2025'),
  ('NSF Astronomy Coordination Agreement', 'Agreement to minimize interference with observatories', 'regulatory', 'completed', '2025-03-15', 'MAR 2025'),
  ('53+ MNOs / 3.2B Subscribers', 'Global carrier partnerships covering 40% of world population', 'commercial', 'completed', '2025-11-15', 'NOV 2025'),
  ('338K sqft Mfg (Midland/FL/Spain)', '74% expansion of manufacturing capacity', 'production', 'completed', '2025-07-15', 'JUL 2025'),
  ('Vodafone/Malaga Research Center', 'European R&D partnership with University of Malaga', 'technical', 'completed', '2025-02-15', 'FEB 2025'),
  ('Singapore DSTA Deal', 'Defense Science and Technology Agency contract', 'government', 'completed', '2025-04-15', 'APR 2025'),
  ('5G Automotive Association Member', 'Connected autonomous vehicle solutions development', 'commercial', 'completed', '2025-03-15', 'MAR 2025'),
  ('Production Ramp to 6x Sats/Month', 'Reached 6x/month with AST5000 ASIC and 338K sqft capacity', 'production', 'completed', '2025-12-15', 'DEC 2025'),
  ('Verizon Commercial Agreement Signed', 'Binding commercial terms for US market', 'commercial', 'completed', '2025-01-22', 'JAN 2025');
