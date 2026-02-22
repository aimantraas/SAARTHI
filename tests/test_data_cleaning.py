"""
Tests for data cleaning utilities.
"""
import pytest
from leadgen_backend.data_cleaning import (
    extract_emails,
    extract_phones,
    parse_from_q,
    clean_serp_api_data,
    clean_serp_google_data,
    filter_linkedin_urls,
    parse_email_field,
    uniq,
    normalize_email,
    split_title,
    parse_followers,
    role_guess
)


class TestExtractEmails:
    def test_basic_email(self):
        assert extract_emails("Contact: john@example.com") == ["john@example.com"]
    
    def test_multiple_emails(self):
        result = extract_emails("john@example.com and jane@test.org")
        assert "john@example.com" in result
        assert "jane@test.org" in result
    
    def test_no_emails(self):
        assert extract_emails("No emails here") == []
    
    def test_normalizes_to_lowercase(self):
        result = extract_emails("JOHN@EXAMPLE.COM")
        assert result == ["john@example.com"]
    
    def test_deduplicates(self):
        result = extract_emails("john@example.com john@example.com")
        assert result == ["john@example.com"]
    
    def test_empty_string(self):
        assert extract_emails("") == []
    
    def test_none_input(self):
        assert extract_emails(None) == []


class TestExtractPhones:
    def test_basic_phone(self):
        result = extract_phones("+919876543210")
        assert "+919876543210" in result
    
    def test_phone_with_spaces(self):
        result = extract_phones("+91 98765 43210")
        assert len(result) > 0
    
    def test_no_phones(self):
        assert extract_phones("No phones here") == []
    
    def test_empty_string(self):
        assert extract_phones("") == []


class TestParseFromQ:
    def test_comma_rule(self):
        name, headline = parse_from_q("Contact Details John Doe, CEO at Acme Corp")
        assert name == "John Doe"
        assert headline == "CEO at Acme Corp"
    
    def test_strips_contact_details(self):
        name, headline = parse_from_q("Contact Details Jane Smith, Director")
        assert name == "Jane Smith"
        assert headline == "Director"
    
    def test_no_comma_fallback(self):
        name, headline = parse_from_q("Contact Details John Doe at Acme")
        assert name == "John Doe"
        assert headline == "at Acme"
    
    def test_empty_string(self):
        name, headline = parse_from_q("")
        assert name is None
        assert headline is None
    
    def test_none_input(self):
        name, headline = parse_from_q(None)
        assert name is None
        assert headline is None


class TestFilterLinkedInUrls:
    def test_keeps_profile_urls(self):
        urls = ["https://linkedin.com/in/johndoe"]
        result = filter_linkedin_urls(urls)
        assert "https://linkedin.com/in/johndoe" in result
    
    def test_drops_company_urls(self):
        urls = ["https://linkedin.com/company/acme"]
        result = filter_linkedin_urls(urls)
        assert len(result) == 0
    
    def test_deduplicates(self):
        urls = ["https://linkedin.com/in/johndoe", "https://linkedin.com/in/johndoe"]
        result = filter_linkedin_urls(urls)
        assert len(result) == 1
    
    def test_mixed_urls(self):
        urls = [
            "https://linkedin.com/in/johndoe",
            "https://linkedin.com/company/acme",
            "https://linkedin.com/in/janedoe"
        ]
        result = filter_linkedin_urls(urls)
        assert len(result) == 2
        assert "https://linkedin.com/company/acme" not in result


class TestParseEmailField:
    def test_plain_string(self):
        primary, secondary = parse_email_field("john@example.com")
        assert primary == "john@example.com"
        assert secondary == ""
    
    def test_json_array(self):
        primary, secondary = parse_email_field('["john@example.com", "jane@example.com"]')
        assert primary == "john@example.com"
        assert secondary == "jane@example.com"
    
    def test_python_list(self):
        primary, secondary = parse_email_field(["john@example.com", "jane@example.com"])
        assert primary == "john@example.com"
        assert secondary == "jane@example.com"
    
    def test_empty_string(self):
        primary, secondary = parse_email_field("")
        assert primary == ""
        assert secondary == ""
    
    def test_none(self):
        primary, secondary = parse_email_field(None)
        assert primary == ""
        assert secondary == ""
    
    def test_normalizes_to_lowercase(self):
        primary, secondary = parse_email_field("JOHN@EXAMPLE.COM")
        assert primary == "john@example.com"


class TestSplitTitle:
    def test_dash_separator(self):
        name, headline = split_title("John Doe - CEO at Acme")
        assert name == "John Doe"
        assert headline == "CEO at Acme"
    
    def test_pipe_separator(self):
        name, headline = split_title("John Doe | CEO | Acme Corp")
        assert name == "John Doe"
        assert headline == "CEO | Acme Corp"
    
    def test_no_separator(self):
        name, headline = split_title("John Doe CEO")
        assert name is None
        assert headline == "John Doe CEO"
    
    def test_empty_string(self):
        name, headline = split_title("")
        assert name is None
        assert headline is None


class TestParseFollowers:
    def test_k_suffix(self):
        result = parse_followers("5K followers")
        assert result == 5000
    
    def test_m_suffix(self):
        result = parse_followers("1.5M followers")
        assert result == 1500000
    
    def test_plain_number(self):
        result = parse_followers("500 followers")
        assert result == 500
    
    def test_no_followers(self):
        result = parse_followers("No followers here")
        assert result is None
    
    def test_none_input(self):
        result = parse_followers(None)
        assert result is None


class TestRoleGuess:
    def test_hod(self):
        assert role_guess("Head of Department") == "HOD"
    
    def test_dean(self):
        assert role_guess("Dean of Engineering") == "Dean"
    
    def test_director(self):
        assert role_guess("Director of Operations") == "Director"
    
    def test_professor(self):
        assert role_guess("Professor at IIT") == "Professor"
    
    def test_assistant_professor(self):
        assert role_guess("Assistant Professor") == "Assistant Professor"
    
    def test_no_match(self):
        assert role_guess("Software Engineer") is None


class TestCleanSerpApiData:
    def test_basic_payload(self):
        payload = {
            "search_parameters": {
                "q": "Contact Details John Doe, CEO at Acme",
                "engine": "google_ai_mode"
            },
            "search_metadata": {
                "id": "test123",
                "created_at": "2024-01-01"
            },
            "text_blocks": [
                {
                    "type": "paragraph",
                    "snippet": "John Doe is the CEO at Acme Corp. Email: john@acme.com"
                }
            ],
            "references": []
        }
        
        result = clean_serp_api_data(payload)
        
        assert result.name == "John Doe"
        assert result.headline == "CEO at Acme"
        assert "john@acme.com" in result.emails
        assert result.meta.id == "test123"
    
    def test_empty_payload(self):
        result = clean_serp_api_data({})
        assert result.name is None
        assert result.emails == []
        assert result.phones == []


class TestUniq:
    def test_removes_duplicates(self):
        result = uniq(["a", "b", "a", "c"])
        assert result == ["a", "b", "c"]
    
    def test_preserves_order(self):
        result = uniq(["c", "a", "b"])
        assert result == ["c", "a", "b"]
    
    def test_empty_list(self):
        assert uniq([]) == []
    
    def test_removes_empty_strings(self):
        result = uniq(["a", "", "b"])
        assert result == ["a", "b"]
