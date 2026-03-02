# Agent Context & Conventions

## Project Context

# GEO Analytics Service - Project Brief

## Overview

GEO (Generative Engine Optimization) Analytics Service measures and optimizes drug visibility across AI chat platforms (ChatGPT, Claude, Gemini). It answers: "When patients or doctors ask AI about treatments, how often is our drug mentioned, in what position, and with what sentiment?"

**Primary Use Case**: Specialty pharmacy competitive analytics - track share of voice for drugs like Inflectra across LLM conversations.

## Goals

- [x] Track drug mentions across ChatGPT, Claude, and Gemini
- [x] Extract positioning, sentiment, and competitive context
- [x] Support multi-tenant organizations
- [x] Enable reproducible query execution with model parameters
- [ ] Content production for GEO optimization
- [ ] Self-hosted optimized content distribution

## Non-Goals

- Not a patient-facing chatbot
- Not real-time monitoring (batch analytics)
- Not medical advice generation

## Query Framework

Queries are constructed with configurable parameters to cover realistic search scenarios:

| Parameter | Examples |
|-----------|----------|
| **Persona** | Patient demographics, health literacy levels, HCP specialties |
| **Affect** | Anxious, clinical, casual, distressed |
| **Intent** | Awareness, consideration, decision |
| **Conversation stage** | First query, follow-up, multi-turn |

**Example Query Matrix:**
```
Persona: "Frustrated patient, low health literacy"
Affect: Distressed
Queries:
- "What are my treatment options for psoriasis?"
- "I'm at my wits end, I have horrible joint pain, what should I do?"
```

## Core Metrics (MVP)

### 1. Visibility & Share of Voice (HIGH PRIORITY)

| Metric | Description |
|--------|-------------|
| Mention rate | % of queries where drug appears |
| First mention position | Character/sentence position in response |
| Mention frequency | Times mentioned per response |
| Exclusive mentions | % where it's the only drug mentioned |
| Category ownership | % of indication queries where it appears |

### 2. Positioning & Ranking (HIGH PRIORITY)

| Metric | Description |
|--------|-------------|
| Recommendation order | 1st/2nd/3rd drug recommended |
| List position | Where it appears in bulleted lists |
| Comparative framing | "preferred", "alternative", "last-line" |
| Conditional positioning | "If X fails, consider Y" dependencies |

### 3. Sentiment & Framing (MEDIUM PRIORITY)

| Metric | Description |
|--------|-------------|
| Overall valence | Positive/neutral/negative |
| Aspect sentiment | Separate scores for efficacy, safety, convenience, cost |
| Hedge language | "May", "possibly", "limited evidence" density |
| Endorsement strength | "Recommended" vs "consider" vs "available option" |

### 4. Clinical Context Quality (MEDIUM-HIGH PRIORITY)

| Metric | Description |
|--------|-------------|
| Indication accuracy | Correct FDA-approved uses mentioned |
| Side effect prominence | How early/extensively discussed |
| Contraindication mentions | Key warnings surfacing |
| Evidence citation style | "Studies show" vs "limited data suggests" |

### 5. Competitive Dynamics (MEDIUM PRIORITY)

| Metric | Description |
|--------|-------------|
| Co-mention network | Which drugs appear together |
| Head-to-head comparisons | When directly compared, who "wins" |
| Substitution patterns | Mentioned as alternative to which drugs |
| Therapy sequence | 1st-line, 2nd-line positioning |

## Content Production Phase

### Capabilities

1. **Discovery & Audit**
   - Search for brand across web (FireCrawl)
   - Identify where brand is/isn't discoverable
   - Surface missed opportunities (e.g., drug not on Mayo Clinic treatment page)

2. **Content Scraping & Processing**
   - Crawl official brand content
   - Markdownify for AI readability
   - Store in object storage (MinIO)

3. **GEO-Optimized Content Production**
   - Reformat for AI digestibility
   - Short FAQ-style citable dialogues
   - Position brand based on identified weaknesses

4. **Distribution**
   - Self-hosted content with optimized sitemap
   - Portfolio for content partner distribution
   - Recommendations for actions beyond content (studies, outreach)

## Domain Context

### Drug-Brand Relationship

```
infliximab (molecule)
├── Remicade (reference brand)
└── Biosimilars:
    ├── Inflectra (target)
    ├── Renflexis
    ├── Avsola
    └── Ixifi
```

**Attribution Rules:**
- Generic only ("infliximab") → benefits category, partial credit to all biosimilars
- Generic + brands → split equally among mentioned brands
- Brand only ("Inflectra") → full credit to that brand

### Key Terms

| Term | Definition |
|------|------------|
| **GEO** | Generative Engine Optimization - optimizing for AI chat visibility |
| **Share of Voice** | % of conversations mentioning your drug |
| **Biosimilar** | FDA-approved alternative to reference biologic |
| **Reference Product** | Original biologic (e.g., Remicade) |
| **TNF Inhibitor** | Drug class including infliximab, adalimumab |

## External Integrations

| Service | Purpose | Status |
|---------|---------|--------|
| OpenAI | ChatGPT query execution | Active |
| Anthropic | Claude query execution | Active |
| Google | Gemini query execution | Active |
| FireCrawl | Web scraping/crawling | Active |
| MinIO | Object storage for content | Active |
| PostgreSQL | Primary database | Active |
| Redis | Task queue (Arq) | Active |

## Architecture

```
ConversationInstance → ConversationLog → Extraction → Metric
      (query)           (LLM response)   (entities)   (aggregated)
```

See `.architecture/adr/` for detailed decisions.

## Influence Strategy (Beyond Measurement)

The goal is to become *genuinely more worthy of mention*, not game LLMs. Measurement informs action:

### High-Impact Levers

| Lever | Why It Works | Investment |
|-------|--------------|------------|
| **RWE Publications** | LLMs trained on published literature | $500K-2M, 18-24 months |
| **Guideline Inclusion** | ACR/ACG guidelines heavily influence training | 24-36 months |
| **UpToDate/Epocrates** | Medical databases with high LLM weighting | $50K, 6-12 months |
| **Wikipedia Accuracy** | High visibility, easy baseline | $5K, 1-3 months |
| **Open-Access Journals** | Prioritized in LLM training (PubMed Central, PLOS) | Varies |

### What Doesn't Work

- **Paying LLM companies** - No preferential mentions mechanism exists
- **Press releases alone** - Low training data signal
- **Social media ads** - De-weighted or excluded from training
- **Content farms/astroturfing** - Detectable, unethical, backfires
- **Direct fine-tuning** - Can't fine-tune general Claude/GPT

### Measurement → Action Workflow

```
Gap: "Inflectra mentioned 15% for AS vs Avsola 45%"
    ↓
Action: Commission AS-specific RWE study
    ↓
Amplify: Present at ACR, publish open-access
    ↓
Re-measure: Expect 15% → 35% in 12 months
```

### Ethical Constraints

- ✅ Discuss FDA-approved indications
- ✅ Publish peer-reviewed studies (academic freedom)
- ✅ Ensure accurate safety information available
- ❌ Promote off-label uses
- ❌ Claim superiority without head-to-head data

## Security Considerations

- API keys stored in environment variables
- Organization-scoped data access
- No PII in conversation logs
- Rate limiting per organization

## For AI Agents

### Priority Tasks

1. Content scraping and GEO optimization pipeline
2. Dashboard for metrics visualization
   - Handle query add/remove: adding starts tracking (can't backfill), removing hides metric contributions
3. Automated extraction improvements
   - Extraction error replay/debugging for diagnosing failures
4. Query templates for reusable patterns (e.g., "why do some patients stop taking {drug}")
5. Conversation seeds for auto-generating conversation instances from UI
6. Incremental script processing (skip already-processed items)

### Areas Requiring Caution

- Rate limits on LLM APIs (budget controls in place)
- Drug-brand relationship accuracy
- FDA compliance for medical claims

### Preferred Patterns

- See CLAUDE.md for code style
- See AGENTS.md for agent conventions
- Use structured logging throughout
- Pydantic for all validation


## Core Architecture

