# LeadGen Backend — Python LinkedIn Lead Generation System

A powerful Python backend implementation of LinkedIn lead generation workflows, providing automated lead generation, enrichment, and email verification. This system integrates with SerpAPI, Apify, EmailVerify.io, and Google Sheets to streamline B2B lead discovery.

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](#license)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

</div>

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW 1 — LeadGen + Enrichment             │
│                                                                   │
│  ManualTrigger → InitConstants → SplitInBatches (batchSize=1)   │
│       ↓                                                           │
│  SerpAPI Google Search (site:linkedin.com/in {company} {pos})   │
│       ↓                                                           │
│  CleanData1 (parse organic results, extract name/headline)       │
│       ↓                                                           │
│  FilterURLs (keep /in/, drop /company/, dedup)                   │
│       ↓                                                           │
│  Apify LinkedIn Profile Scraper (profileUrls[])                  │
│       ↓                                                           │
│  SerpAPI AI Mode (Contact Details {name}, {company})             │
│       ↓                                                           │
│  DataCleaning (emails, phones, address, about, sources)          │
│       ↓                                                           │
│  Merge (LinkedIn + SerpAPI data by linkedinUrl)                  │
│       ↓                                                           │
│  Google Sheets appendOrUpdate (match: LinkedInUrl)               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    WORKFLOW 2 — Email Verification               │
│                                                                   │
│  ScheduleTrigger → LoadSheets (filter: email verification=PROCESS)│
│       ↓                                                           │
│  SplitOut (flatten Email[] arrays)                               │
│       ↓                                                           │
│  ParseEmails (primary, secondary, lowercase+trim)                │
│       ↓                                                           │
│  Lookup (skip already-verified)                                  │
│       ↓                                                           │
│  EmailVerify.io HTTP GET                                         │
│       ↓                                                           │
│  StatusSwitch (5 routes):                                        │
│    valid → status="valid", email verification="valid"            │
│    invalid → status="invalidEmail"                               │
│    catch_all → status="catch_all"                                │
│    role_based → status="notEmail"                                │
│    unknown → Requeue → status="PROCESS"                          │
│       ↓                                                           │
│  Google Sheets appendOrUpdate (match: Email)                     │
└─────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
leadgen_backend/
├── __init__.py              # Package exports
├── config.py                # Configuration and constants
├── models.py                # Data models
├── data_cleaning.py         # Data cleaning utilities (ported from N8N JS)
├── sheets.py                # Google Sheets integration
├── clients/
│   ├── __init__.py
│   ├── serp_api.py          # SerpAPI client
│   ├── apify.py             # Apify LinkedIn scraper client
│   └── email_verify.py      # Email verification client
└── workflows/
    ├── __init__.py
    ├── leadgen.py           # Workflow 1: LeadGen + Enrichment
    └── email_verify.py      # Workflow 2: Email Verification

main.py                      # CLI entry point
wsgi.py                      # WSGI server entry point
app.py                       # Flask web API
requirements.txt             # Python dependencies
.env.example                 # Environment variables template
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your API keys
```

Required environment variables:
- `SERP_API_KEY` — SerpAPI key
- `APIFY_API_TOKEN` — Apify API token
- `EMAIL_VERIFY_API_KEY` — EmailVerify.io API key
- `GOOGLE_SHEET_ID` — Google Spreadsheet ID
- `GOOGLE_CREDENTIALS_PATH` — Path to Google OAuth2 credentials JSON

### 3. Google Sheets Authentication

1. Create a Google Cloud project
2. Enable Google Sheets API
3. Create OAuth2 credentials
4. Download credentials JSON to `credentials.json`
5. First run will open browser for authentication

## Usage

### CLI Commands

```bash
# Test configuration
python main.py test-config

# Run lead generation
python main.py leadgen --companies "Retail" "Tech" --position "CEO" --country "India"

# Run email verification
python main.py email-verify --limit 50

# Run full pipeline
python main.py pipeline --companies "Retail" --position "Head operation"

# Run scheduled email verification (every hour)
python main.py schedule --interval 3600 --limit 50

```

### Web API (Flask)

This repo also includes a Flask web UI/API in `app.py`.

Run in development (built-in server):

```powershell
python app.py
```

Run in production (recommended WSGI server – no "development server" warning):

```powershell
pip install -r requirements.txt
waitress-serve --host=0.0.0.0 --port=5000 wsgi:app
```

Optional environment variables:
- `HOST` (default `0.0.0.0`)
- `PORT` (default `5000`)
- `FLASK_DEBUG=1` (enable debug mode for development)
- `PRODUCTION=1` or `USE_WAITRESS=1` (serve via Waitress when running `python app.py`)

### Python API

```python
import asyncio
from leadgen_backend import (
    LeadGenConfig,
    GoogleSheetsClient,
    run_leadgen_workflow,
    run_email_verification
)

async def main():
    config = LeadGenConfig(
        serp_api_key="your_key",
        apify_api_token="your_token",
        email_verify_api_key="your_key",
        google_sheet_id="your_sheet_id",
        companies=["Retail", "Tech"],
        position="Head operation",
        country="India",
        country_code="IN"
    )
    
    sheets = GoogleSheetsClient(config)
    
    # Run lead generation
    records = await run_leadgen_workflow(
        config=config,
        sheets_client=sheets,
        sheet_name="Retail Apparel"
    )
    print(f"Generated {len(records)} leads")
    
    # Run email verification
    results = await run_email_verification(
        config=config,
        sheets_client=sheets,
        sheet_name="Retail Apparel",
        batch_limit=50
    )
    print(f"Verified {len(results)} emails")

asyncio.run(main())
```

## Google Sheets Schema

The system writes to Google Sheets with these columns:

| Column | Description |
|--------|-------------|
| LinkedinUrl | LinkedIn profile URL (match key) |
| FullName | Full name |
| FirstName | First name |
| LastName | Last name |
| Connections | LinkedIn connections count |
| Follower | Follower display text |
| Email | Email address(es) |
| email verification | Verification status |
| mobileNumber | Phone number |
| headline | LinkedIn headline |
| address Country Only | Country |
| jobTitle | Current job title |
| jobLocation | Job location |
| companyName | Company name |
| companyIndustry | Industry |
| companyWebsite | Company website |
| companyLinkedin | Company LinkedIn URL |
| companySize | Company size |
| jobStartedOn | Job start date |
| currentJobDuration | Duration in current role |
| addressWithoutCountry | Address without country |
| followers | Follower count |
| snippet | Search snippet |
| emailType | Email type |
| status | Verification status |
| about | About section |
| name | Name from SerpAPI |
| displayed_link | Displayed link |

## Email Verification Status Values

| Status | Description |
|--------|-------------|
| `valid` | Email is valid and deliverable |
| `invalid` / `invalidEmail` | Email is invalid |
| `catch_all` | Domain accepts all emails |
| `role_based` / `notEmail` | Role-based email (info@, admin@) |
| `unknown` | Could not determine status |
| `PROCESS` | Queued for verification |

## Data Cleaning Logic

The `data_cleaning.py` module ports the N8N JavaScript code nodes to Python:

### `clean_serp_api_data(payload)` — DataCleaning node
- Parses AI text blocks from SerpAPI google_ai_mode
- Extracts emails via regex + SerpAPI emails, deduplicates
- Extracts phones via regex from text_blocks
- Pulls location from text_blocks or address field
- Parses name/headline using comma-rule
- Normalizes and builds contact object

### `clean_serp_google_data(payload)` — CleanData1 node
- Parses organic results from SerpAPI Google search
- Splits title into name/headline (by dash or pipe)
- Estimates follower count from displayed_link
- Guesses role from title/snippet
- Detects India-based profiles

### `parse_email_field(email_field)` — Code in JavaScript2 node
- Handles string, array, or JSON-stringified array formats
- Returns (primary_email, secondary_email) tuple

## Rate Limiting

The system includes built-in rate limiting:
- SerpAPI: 2-5 second random wait between requests
- Apify: 2-5 second wait between batches
- Email Verify: 1-2 second wait between verifications

## Error Handling

- API errors are caught and logged, processing continues
- Failed email verifications are marked as `unknown` (requeued)
- Failed profile scrapes are skipped
- All errors include stack traces in debug mode

## Testing

Run automated tests to verify the system:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=leadgen_backend

# Run specific test file
pytest tests/test_data_cleaning.py

# Run tests with verbose output
pytest -v
```

Test files:
- `test_config.py` — Configuration and initialization tests
- `test_api.py` — API endpoint tests
- `test_email_api.py` — Email verification client tests
- `tests/test_data_cleaning.py` — Data cleaning logic tests

## Development Setup

### Local Development

1. Clone the repository with submodules:
```bash
git clone --recurse-submodules https://github.com/aimantraas/SAARTHI.git
cd "emali system"
```

2. Create and activate virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. Install development dependencies:
```bash
pip install -r requirements.txt
pip install black isort flake8 mypy
```

### Code Quality

This project uses:
- **black** — Code formatting
- **isort** — Import sorting
- **flake8** — Linting
- **mypy** — Type checking

Run code quality checks:
```bash
black leadgen_backend tests
isort leadgen_backend tests
flake8 leadgen_backend tests
mypy leadgen_backend
```

## Submodules

This repository includes the **Saarethi** project as a submodule:

```bash
# Update submodule
git submodule update --init --recursive

# Clone with submodules
git clone --recurse-submodules https://github.com/aimantraas/SAARTHI.git
```

See [Saarethi Repository](https://github.com/aimantraas/Saarethi) for details.

## Production Deployment

For production deployments:

1. Use a production WSGI server (Waitress, Gunicorn, uWSGI)
2. Configure environment variables properly
3. Set `PRODUCTION=1` or `USE_WAITRESS=1`
4. Use proper logging and monitoring
5. Implement rate limiting on the frontend

## Troubleshooting

### Common Issues

**Google Sheets Authentication Fails**
- Ensure `credentials.json` is in the project root
- Check Google OAuth2 scopes include Google Sheets API
- Try regenerating credentials in Google Cloud Console

**API Rate Limiting**
- Reduce batch size with `--per-page` flag
- Increase delays in `config.py`
- Implement request queuing on production

**Email Verification Slow**
- Increase `--limit` parameter
- Run multiple verification instances with different sheet ranges
- Check API quota in EmailVerify.io dashboard

**LinkedIn Profile Scraping Fails**
- Verify Apify API token is valid
- Check Apify actor availability
- Ensure LinkedIn URLs are public profiles

### Debug Mode

Enable debug logging:
```bash
export FLASK_DEBUG=1
python app.py
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Follow code style guidelines (black, isort, flake8)
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## Support

For issues, feature requests, or questions:
- Open an [issue](https://github.com/aimantraas/SAARTHI/issues) on GitHub
- Check documentation for common questions

## Changelog

### v1.0.0 (Current)
- LinkedIn lead generation with SerpAPI
- Apify profile scraping
- Email verification integration
- Google Sheets integration
- Email verification workflow scheduling
- Flask web API
- Comprehensive data cleaning

---

**Built with ❤️ by [aimantraas](https://github.com/aimantraas)**
