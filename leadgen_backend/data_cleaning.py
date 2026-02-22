"""
Data cleaning utilities for the LeadGen system.
Ported from N8N JavaScript Code nodes to Python.
"""
import re
from typing import List, Optional, Dict, Any, Tuple
from urllib.parse import urlparse

from .models import SerpAPIResult, OrganicResult, MetaInfo, ContactInfo


def uniq(items: List[str]) -> List[str]:
    """Return unique items preserving order."""
    seen = set()
    result = []
    for item in items:
        trimmed = str(item).strip() if item else ""
        if trimmed and trimmed not in seen:
            seen.add(trimmed)
            result.append(trimmed)
    return result


def normalize_email(email: str) -> Optional[str]:
    """Normalize and validate an email address."""
    if not email:
        return None
    email = str(email).strip().lower()
    pattern = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
    if re.match(pattern, email):
        return email
    return None


def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text."""
    if not text:
        return []
    pattern = r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}'
    matches = re.findall(pattern, str(text), re.IGNORECASE)
    return uniq([e for e in [normalize_email(m) for m in matches] if e])


def extract_phones(text: str) -> List[str]:
    """Extract phone numbers from text."""
    if not text:
        return []
    # Match phone-like patterns
    raw_matches = re.findall(r'\+?\d[\d()\-\s]{6,}', str(text))
    
    result = []
    for match in raw_matches:
        # Remove non-digit characters except leading +
        cleaned = re.sub(r'[^\d+]', '', match)
        
        # Validate length
        if re.match(r'^\+?\d{7,15}$', cleaned) or re.match(r'^\d{10,15}$', cleaned):
            if not cleaned.startswith('+') and len(cleaned) >= 10:
                cleaned = '+' + cleaned
            if cleaned.startswith('+'):
                result.append(cleaned)
    
    return uniq(result)


def links_from_references(refs: List[Dict]) -> List[str]:
    """Extract links from references array."""
    out = []
    for ref in refs or []:
        if ref.get('link'):
            out.append(ref['link'])
        snippet = str(ref.get('snippet', ''))
        found = re.findall(r'https?://[^\s)]+', snippet)
        out.extend(found)
    return uniq(out)


def address_from_blocks(blocks: List[Dict]) -> Optional[str]:
    """Extract address from text blocks."""
    location_keywords = [
        'Address:', 'Location:', 'Road', 'Campus', 'Ghaziabad', 'Indore',
        'Nagpur', 'Gorakhpur', 'Jhalawar', 'Karnataka', 'India', 'PIN:',
        'Uttar', 'Rajasthan'
    ]
    pattern = '|'.join(re.escape(kw) for kw in location_keywords)
    loc_key = re.compile(f'({pattern})', re.IGNORECASE)
    
    for block in blocks or []:
        if block.get('type') == 'list' and isinstance(block.get('list'), list):
            for li in block['list']:
                text = str(li.get('snippet', '')).strip()
                if loc_key.search(text):
                    return re.sub(r'^(Address:|Location:)\s*', '', text, flags=re.IGNORECASE).strip()
        elif block.get('type') == 'paragraph':
            text = str(block.get('snippet', '')).strip()
            if loc_key.search(text):
                return re.sub(r'^(Address:|Location:)\s*', '', text, flags=re.IGNORECASE).strip()
    
    return None


def emails_phones_from_blocks(blocks: List[Dict]) -> Tuple[List[str], List[str]]:
    """Extract emails and phones from text blocks."""
    emails = []
    phones = []
    
    for block in blocks or []:
        if block.get('type') == 'list' and isinstance(block.get('list'), list):
            for li in block['list']:
                snippet = str(li.get('snippet', ''))
                emails.extend(extract_emails(snippet))
                phones.extend(extract_phones(snippet))
        elif block.get('type') == 'paragraph':
            snippet = str(block.get('snippet', ''))
            emails.extend(extract_emails(snippet))
            phones.extend(extract_phones(snippet))
    
    return uniq(emails), uniq(phones)


def build_about(blocks: List[Dict]) -> Optional[str]:
    """Build about text from paragraph blocks."""
    paragraphs = []
    for block in blocks or []:
        if block.get('type') == 'paragraph':
            snippet = str(block.get('snippet', '')).strip()
            if snippet:
                paragraphs.append(snippet)
    
    return ' '.join(paragraphs[:2]) if paragraphs else None


def parse_from_q(q_raw: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Parse name and headline from search query.
    Rule: before first comma = name, after = headline
    """
    if not q_raw:
        return None, None
    
    # Strip "Contact Details" prefix
    q = re.sub(r'^\s*Contact\s+Details\s*', '', str(q_raw).strip(), flags=re.IGNORECASE).strip()
    
    # Fix glued tokens like "Institute , Training"
    q = re.sub(r'\s*,\s*', ', ', q)
    q = re.sub(r'\s{2,}', ' ', q).strip()
    
    # Primary rule: split on first comma
    first_comma = q.find(',')
    if first_comma != -1:
        name = q[:first_comma].strip() or None
        headline = q[first_comma + 1:].strip() or None
        return name, headline
    
    # Fallback: try "role at org" split
    at_idx = q.lower().find(' at ')
    if at_idx > 0:
        return q[:at_idx].strip() or None, q[at_idx + 1:].strip() or None
    
    # Final fallback: whole string becomes name
    return q or None, None


def clean_serp_api_data(payload: Dict[str, Any]) -> SerpAPIResult:
    """
    Clean and structure contact data from SerpAPI google_ai_mode results.
    Equivalent to N8N DataCleaning Code node.
    """
    q = payload.get('search_parameters', {}).get('q')
    blocks = payload.get('text_blocks', [])
    refs = payload.get('references', [])
    
    name, headline = parse_from_q(q)
    emails, phones = emails_phones_from_blocks(blocks)
    about = build_about(blocks)
    address = address_from_blocks(blocks)
    sources = links_from_references(refs)
    
    meta = MetaInfo(
        query=q,
        engine=payload.get('search_parameters', {}).get('engine'),
        id=payload.get('search_metadata', {}).get('id'),
        created_at=payload.get('search_metadata', {}).get('created_at')
    )
    
    return SerpAPIResult(
        name=name,
        headline=headline,
        emails=emails,
        phones=phones,
        about=about,
        address=address,
        sources=sources,
        meta=meta
    )


def parse_followers(text: str) -> Optional[int]:
    """Parse follower count from displayed_link text."""
    if not text:
        return None
    match = re.search(r'([\d.,]+)\s*\+?\s*(k|m)?\s*followers', str(text), re.IGNORECASE)
    if not match:
        return None
    
    n = float(match.group(1).replace(',', ''))
    unit = (match.group(2) or '').lower()
    
    if unit == 'k':
        n *= 1_000
    elif unit == 'm':
        n *= 1_000_000
    
    return round(n)


def role_guess(text: str) -> Optional[str]:
    """Guess role from title/snippet text."""
    t = str(text or '').lower()
    
    if re.search(r'(head of department|[^a-z]hod[^a-z])', t, re.IGNORECASE):
        return 'HOD'
    if re.search(r'\bdean\b', t):
        return 'Dean'
    if re.search(r'\bdirector\b', t):
        return 'Director'
    if re.search(r'\bprincipal\b', t):
        return 'Principal'
    if re.search(r'\bassistant professor\b', t):
        return 'Assistant Professor'
    if re.search(r'\bassociate professor\b', t):
        return 'Associate Professor'
    if re.search(r'\bprofessor\b', t):
        return 'Professor'
    if re.search(r'\blecturer\b', t):
        return 'Lecturer'
    
    return None


def split_title(title: str) -> Tuple[Optional[str], Optional[str]]:
    """Split title into name and headline."""
    if not title:
        return None, None
    
    # Try splitting by dash
    by_dash = str(title).split(' - ')
    if len(by_dash) > 1:
        return by_dash[0].strip(), ' - '.join(by_dash[1:]).strip() or None
    
    # Try splitting by pipe
    by_pipe = str(title).split(' | ')
    if len(by_pipe) > 1:
        return by_pipe[0].strip(), ' | '.join(by_pipe[1:]).strip() or None
    
    return None, str(title).strip()


def pick_location_and_org(extensions: List[str]) -> Tuple[Optional[str], Optional[str]]:
    """Pick location and organization hints from extensions."""
    if not isinstance(extensions, list):
        return None, None
    
    location_pattern = re.compile(
        r'India|Delhi|Mumbai|Bengaluru|Bangalore|Chennai|Hyderabad|Kolkata|Pune|'
        r'Ahmedabad|Uttar|Maharashtra|Tamil Nadu|Karnataka|Gujarat|Punjab|Rajasthan|'
        r'Madhya Pradesh|Uttarakhand|Chhattisgarh|Andhra|Telangana|Kerala|Assam|'
        r'Bihar|Jharkhand|Odisha|Goa|Haryana|Jammu|Kashmir|Himachal|Tripura|'
        r'Manipur|Mizoram|Meghalaya|Nagaland|Sikkim|Chandigarh|Puducherry',
        re.IGNORECASE
    )
    
    loc_idx = None
    for i, ext in enumerate(extensions):
        if location_pattern.search(str(ext or '')):
            loc_idx = i
            break
    
    location_hint = extensions[loc_idx] if loc_idx is not None else None
    org_hint = next((ext for i, ext in enumerate(extensions) if i != loc_idx), None)
    
    return location_hint, org_hint


def host_info(link: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract hostname and TLD from URL."""
    try:
        parsed = urlparse(link)
        hostname = parsed.hostname
        tld = hostname.split('.')[-1] if hostname else None
        return hostname, tld
    except Exception:
        return None, None


def clean_serp_google_data(payload: Dict[str, Any]) -> List[OrganicResult]:
    """
    Clean and structure data from SerpAPI Google search results.
    Equivalent to N8N CleanData1 Code node.
    """
    results = []
    
    # Handle both raw object and wrapped array
    data = payload[0] if isinstance(payload, list) and len(payload) > 0 else payload
    
    if not data or not data.get('organic_results'):
        return results
    
    q = data.get('search_parameters', {}).get('q')
    next_page = data.get('serpapi_pagination', {}).get('next')
    search_id = data.get('search_metadata', {}).get('id')
    
    for r in data.get('organic_results', []):
        title = r.get('title')
        name, headline = split_title(title)
        link = r.get('link')
        snippet = r.get('snippet')
        followers_est = parse_followers(r.get('displayed_link', ''))
        
        extensions = r.get('rich_snippet', {}).get('top', {}).get('extensions', [])
        location_hint, org_hint = pick_location_and_org(extensions)
        
        hostname, tld_country = host_info(link)
        role = role_guess(f"{title} {snippet}")
        
        # Check if India-based
        is_india = (
            re.search(r'(^|[\s,])India([\s,]|$)', f"{location_hint or ''} {snippet or ''}", re.IGNORECASE) is not None
            or (hostname and hostname.endswith('.in'))
            or tld_country == 'in'
        )
        
        results.append(OrganicResult(
            search_id=search_id,
            query=q,
            position=r.get('position'),
            page_next=next_page,
            name=name,
            headline=headline,
            role_guess=role,
            link=link,
            linkedin_host=hostname,
            tld_country=tld_country,
            is_india=is_india,
            followers_est=followers_est,
            snippet=snippet,
            location_hint=location_hint,
            org_hint=org_hint,
            source=r.get('source'),
            displayed_link=r.get('displayed_link'),
            favicon=r.get('favicon')
        ))
    
    return results


def filter_linkedin_urls(urls: List[str]) -> List[str]:
    """Filter LinkedIn URLs to keep only profile URLs, exclude company pages."""
    filtered = []
    for url in urls:
        if not url:
            continue
        if '/in/' in url and '/company/' not in url:
            filtered.append(url)
    return uniq(filtered)


def parse_email_field(email_field: Any) -> Tuple[str, str]:
    """
    Parse email field which may be a string, array, or JSON string.
    Returns (primary_email, secondary_email).
    """
    import json
    
    email = ''
    email2 = ''
    
    if not email_field:
        return email, email2
    
    if isinstance(email_field, list):
        email = email_field[0] if len(email_field) > 0 else ''
        email2 = email_field[1] if len(email_field) > 1 else ''
    elif isinstance(email_field, str):
        try:
            parsed = json.loads(email_field)
            if isinstance(parsed, list):
                email = parsed[0] if len(parsed) > 0 else ''
                email2 = parsed[1] if len(parsed) > 1 else ''
            else:
                email = parsed or ''
        except (json.JSONDecodeError, TypeError):
            email = email_field
    else:
        email = str(email_field)
    
    return str(email).lower().strip(), str(email2).lower().strip()
