#!/usr/bin/env python3
"""
Web interface for LeadGen Backend.
Provides a simple Flask API to run the lead generation and email verification workflows.
"""
import asyncio
import json
import os
from flask import Flask, request, jsonify, render_template_string
from pathlib import Path

from leadgen_backend import (
    LeadGenConfig,
    GoogleSheetsClient,
    run_leadgen_workflow,
    run_email_verification
)

app = Flask(__name__)

# Configuration - Load after environment variables are set
def load_config():
    from leadgen_backend import config
    return config

CONFIG = load_config()

# HTML template for the web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LeadGen Backend</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 2rem;
            color: #333;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        .header {
            text-align: center;
            margin-bottom: 3rem;
            color: white;
        }

        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }

        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }

        .card {
            background: white;
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }

        .card h2 {
            color: #667eea;
            margin-bottom: 1.5rem;
            font-size: 1.5rem;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 0.5rem;
        }

        .form-group {
            margin-bottom: 1.5rem;
        }

        .form-group label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 600;
            color: #555;
        }

        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 0.75rem;
            border: 2px solid #e1e5e9;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.3s ease;
        }

        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }

        .btn {
            display: inline-block;
            padding: 0.75rem 1.5rem;
            border: none;
            border-radius: 8px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
        }

        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.3);
        }

        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }

        .btn-success {
            background: #10b981;
            color: white;
        }

        .btn-success:hover {
            background: #059669;
        }

        .status {
            padding: 1rem;
            border-radius: 8px;
            margin-top: 1rem;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            white-space: pre-wrap;
            max-height: 400px;
            overflow-y: auto;
        }

        .status.success {
            background: #dcfce7;
            border-color: #bbf7d0;
            color: #166534;
        }

        .status.error {
            background: #fee2e2;
            border-color: #fecaca;
            color: #991b1b;
        }

        .results {
            margin-top: 2rem;
        }

        .results h3 {
            color: #667eea;
            margin-bottom: 1rem;
        }

        .results pre {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 1rem;
            overflow-x: auto;
            white-space: pre-wrap;
            font-size: 0.9rem;
        }

        .config-info {
            background: #f0f9ff;
            border: 1px solid #bae6fd;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            color: #0369a1;
        }

        .config-info ul {
            margin-left: 1.5rem;
            margin-top: 0.5rem;
        }

        .config-info li {
            margin-bottom: 0.25rem;
        }

        @media (max-width: 768px) {
            body {
                padding: 1rem;
            }

            .header h1 {
                font-size: 2rem;
            }

            .card {
                padding: 1.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LeadGen Backend</h1>
            <p>LinkedIn Lead Generation and Email Verification System</p>
        </div>

        <div class="card">
            <h2>Configuration</h2>
            <div class="config-info">
                <p><strong>Current Status:</strong> {{ config_status }}</p>
                <ul>
                    <li><strong>SerpAPI Key:</strong> {{ '✓ Configured' if config.serp_api_key else '✗ Not Configured' }}</li>
                    <li><strong>Apify Token:</strong> {{ '✓ Configured' if config.apify_api_token else '✗ Not Configured' }}</li>
                    <li><strong>Email Verify Key:</strong> {{ '✓ Configured' if config.email_verify_api_key else '✗ Not Configured' }}</li>
                    <li><strong>Google Sheet ID:</strong> {{ '✓ Configured' if config.google_sheet_id else '✗ Not Configured' }}</li>
                    <li><strong>Credentials Path:</strong> {{ config.google_credentials_path }}</li>
                </ul>
            </div>
        </div>

        <div class="card">
            <h2>Lead Generation</h2>
            <form id="leadgenForm">
                <div class="form-group">
                    <label for="companies">Companies (comma-separated)</label>
                    <input type="text" id="companies" name="companies" value="Retail" required>
                </div>
                <div class="form-group">
                    <label for="position">Position</label>
                    <input type="text" id="position" name="position" value="Head operation" required>
                </div>
                <div class="form-group">
                    <label for="country">Country</label>
                    <input type="text" id="country" name="country" value="India" required>
                </div>
                <div class="form-group">
                    <label for="country_code">Country Code</label>
                    <input type="text" id="country_code" name="country_code" value="IN" required>
                </div>
                <div class="form-group">
                    <label for="batch_size">Batch Size</label>
                    <input type="number" id="batch_size" name="batch_size" value="10" min="1" max="100">
                </div>
                <div class="form-group">
                    <label for="mock_sheets">
                        <input type="checkbox" id="mock_sheets" name="mock_sheets">
                        Use Mock Sheets (for testing without Google Sheets API)
                    </label>
                </div>
                <button type="submit" class="btn btn-primary">
                    Run Lead Generation
                </button>
            </form>
            <div id="leadgenStatus" class="status" style="display: none;"></div>
            <div id="leadgenResults" class="results"></div>
        </div>

        <div class="card">
            <h2>Email Verification</h2>
            <form id="emailForm">
                <div class="form-group">
                    <label for="email_limit">Batch Limit</label>
                    <input type="number" id="email_limit" name="email_limit" value="50" min="1" max="1000">
                </div>
                <div class="form-group">
                    <label for="email_mock_sheets">
                        <input type="checkbox" id="email_mock_sheets" name="email_mock_sheets">
                        Use Mock Sheets (for testing without Google Sheets API)
                    </label>
                </div>
                <button type="submit" class="btn btn-primary">
                    Run Email Verification
                </button>
            </form>
            <div id="emailStatus" class="status" style="display: none;"></div>
            <div id="emailResults" class="results"></div>
        </div>
    </div>

    <script>
        // Helper function to update status
        function updateStatus(elementId, message, isError = false) {
            const statusDiv = document.getElementById(elementId);
            statusDiv.textContent += message + '\\n';
            statusDiv.className = 'status' + (isError ? ' error' : '');
            statusDiv.style.display = 'block';
            statusDiv.scrollTop = statusDiv.scrollHeight;
        }

        // Helper function to display results
        function displayResults(elementId, results) {
            const resultsDiv = document.getElementById(elementId);
            resultsDiv.innerHTML = `
                <h3>Results (${results.length} records)</h3>
                <pre>${JSON.stringify(results, null, 2)}</pre>
            `;
        }

        // Lead generation form
        document.getElementById('leadgenForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());

            // Parse companies
            data.companies = data.companies.split(',').map(s => s.trim()).filter(s => s);
            data.batch_size = parseInt(data.batch_size);
            data.mock_sheets = document.getElementById('mock_sheets').checked;

            const statusDiv = document.getElementById('leadgenStatus');
            const resultsDiv = document.getElementById('leadgenResults');
            statusDiv.textContent = '';
            resultsDiv.innerHTML = '';

            updateStatus('leadgenStatus', 'Starting lead generation...');

            try {
                const response = await fetch('/api/leadgen', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data),
                });

                const result = await response.json();

                if (result.success) {
                    updateStatus('leadgenStatus', `✓ Success! Generated ${result.results.length} leads`);
                    displayResults('leadgenResults', result.results);
                } else {
                    updateStatus('leadgenStatus', `✗ Error: ${result.error}`, true);
                }
            } catch (error) {
                updateStatus('leadgenStatus', `✗ Error: ${error.message}`, true);
            }
        });

        // Email verification form
        document.getElementById('emailForm').addEventListener('submit', async (e) => {
            e.preventDefault();

            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());

            data.limit = parseInt(data.email_limit);
            data.mock_sheets = document.getElementById('email_mock_sheets').checked;

            const statusDiv = document.getElementById('emailStatus');
            const resultsDiv = document.getElementById('emailResults');
            statusDiv.textContent = '';
            resultsDiv.innerHTML = '';

            updateStatus('emailStatus', 'Starting email verification...');

            try {
                const response = await fetch('/api/email-verify', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data),
                });

                const result = await response.json();

                if (result.success) {
                    updateStatus('emailStatus', `✓ Success! Verified ${result.results.length} emails`);
                    displayResults('emailResults', result.results);
                } else {
                    updateStatus('emailStatus', `✗ Error: ${result.error}`, true);
                }
            } catch (error) {
                updateStatus('emailStatus', `✗ Error: ${error.message}`, true);
            }
        });
    </script>
</body>
</html>
"""


@app.route('/')
def index():
    """Render the main web interface."""
    # Create a new config instance to ensure it reloads the environment variables
    from leadgen_backend import LeadGenConfig
    config = LeadGenConfig()

    config_status = "Ready" if (
        config.serp_api_key and 
        config.apify_api_token and 
        config.email_verify_api_key and
        config.google_sheet_id
    ) else "Partial Configuration"

    return render_template_string(HTML_TEMPLATE, config=config, config_status=config_status)


@app.route('/api/leadgen', methods=['POST'])
def api_leadgen():
    """API endpoint to run lead generation."""
    try:
        data = request.get_json()

        # Create configuration
        config = LeadGenConfig()
        config.companies = data.get('companies', ['Retail'])
        config.position = data.get('position', 'Head operation')
        config.country = data.get('country', 'India')
        config.country_code = data.get('country_code', 'IN')
        if 'batch_size' in data:
            config.batch_size = data['batch_size']

        # Create sheets client - always use real Google Sheets
        sheets_client = GoogleSheetsClient(config)
        
        # Run real lead generation workflow
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        records = loop.run_until_complete(run_leadgen_workflow(config, sheets_client))
        loop.close()

        # Convert records to dict
        results = [record.__dict__ for record in records]

        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/email-verify', methods=['POST'])
def api_email_verify():
    """API endpoint to run email verification."""
    try:
        data = request.get_json()

        # Create configuration
        config = LeadGenConfig()

        # Create sheets client - always use real Google Sheets
        sheets_client = GoogleSheetsClient(config)
        
        # Run real email verification workflow
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        results = loop.run_until_complete(run_email_verification(config, sheets_client, batch_limit=data.get('limit', 50)))
        loop.close()

        # Convert results to dict
        processed_results = []
        for result in results:
            processed = result.__dict__ if hasattr(result, '__dict__') else result
            processed_results.append(processed)

        return jsonify({
            'success': True,
            'results': processed_results,
            'count': len(processed_results)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/config', methods=['GET'])
def api_config():
    """API endpoint to get current configuration."""
    def _mask(value: str) -> str:
        if not value:
            return ""
        value = str(value)
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:2]}{'*' * (len(value) - 6)}{value[-4:]}"

    return jsonify({
        'serp_api_key_configured': bool(CONFIG.serp_api_key),
        'serp_api_key_masked': _mask(CONFIG.serp_api_key),
        'apify_api_token_configured': bool(CONFIG.apify_api_token),
        'apify_api_token_masked': _mask(CONFIG.apify_api_token),
        'email_verify_api_key_configured': bool(CONFIG.email_verify_api_key),
        'email_verify_api_key_masked': _mask(CONFIG.email_verify_api_key),
        'google_sheet_id_configured': bool(CONFIG.google_sheet_id),
        'google_sheet_id': CONFIG.google_sheet_id,
        'google_credentials_path': CONFIG.google_credentials_path,
        'companies': CONFIG.companies,
        'position': CONFIG.position,
        'country': CONFIG.country,
        'country_code': CONFIG.country_code,
        'batch_size': CONFIG.batch_size,
        'email_batch_limit': CONFIG.email_batch_limit
    })


if __name__ == '__main__':
    def _env_flag(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "5000"))
    debug = _env_flag("FLASK_DEBUG") or _env_flag("DEBUG")
    use_waitress = _env_flag("USE_WAITRESS") or _env_flag("PRODUCTION")

    print("=" * 60)
    print("LeadGen Backend Web Interface")
    print("=" * 60)
    print(f"Configuration Status: {'Complete' if (CONFIG.serp_api_key and CONFIG.apify_api_token and CONFIG.email_verify_api_key) else 'Incomplete'}")
    print(f"  - SerpAPI Key: {'Configured' if CONFIG.serp_api_key else 'Not Configured'}")
    print(f"  - Apify Token: {'Configured' if CONFIG.apify_api_token else 'Not Configured'}")
    print(f"  - Email Verify Key: {'Configured' if CONFIG.email_verify_api_key else 'Not Configured'}")
    print(f"  - Google Sheet ID: {'Configured' if CONFIG.google_sheet_id else 'Not Configured'}")
    print("=" * 60)
    print()
    print(f"Starting web server on http://{host}:{port}")
    print(f"Mode: {'production (waitress)' if use_waitress else ('debug' if debug else 'development')}")
    print("Press Ctrl+C to stop")
    print()

    if use_waitress:
        try:
            from waitress import serve
        except ImportError:
            raise SystemExit(
                "Waitress is not installed. Run: pip install waitress\n"
                "Or start the dev server without USE_WAITRESS/PRODUCTION."
            )
        serve(app, host=host, port=port)
    else:
        app.run(debug=debug, host=host, port=port)
