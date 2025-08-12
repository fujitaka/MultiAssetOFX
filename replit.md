# Overview

This is a financial data application that fetches stock and mutual fund prices and exports them in OFX format. The app supports Japanese stocks (with exchange suffixes), US stocks/ETFs, and Japanese mutual funds. Users input security codes and a target date, and the system automatically classifies the securities, fetches their prices from appropriate data sources, displays results in a table format, and generates downloadable OFX files for financial software integration.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Flask with Jinja2 templating
- **UI Library**: Bootstrap 5 with dark theme support
- **Styling**: Custom CSS with Font Awesome icons
- **Language**: Japanese interface with bilingual error handling
- **Forms**: Server-side form processing with Flash messaging for user feedback

## Backend Architecture
- **Framework**: Flask web application
- **Structure**: Modular design with separated concerns:
  - `app.py`: Application factory and configuration
  - `routes.py`: URL routing and request handling
  - `services/`: Business logic layer with specialized service classes
- **Error Handling**: Comprehensive logging and retry mechanisms
- **Security**: Session management with configurable secret keys

## Data Sources and APIs
- **Yahoo Finance API**: Primary data source for Japanese and US stocks via yfinance library
- **Web Scraping**: Fallback mechanism using BeautifulSoup and trafilatura for mutual fund data
- **Retry Logic**: Configurable retry attempts with exponential backoff for robust data fetching

## Security Classification System
- **Japanese Stocks**: Pattern matching for exchange suffixes (.T, .O, .N, .F, .S)
- **US Securities**: Alphabetic ticker validation
- **Japanese Mutual Funds**: Numeric fund code recognition
- **Auto-detection**: Intelligent classification based on input format patterns

## File Generation
- **OFX Format**: Standards-compliant Open Financial Exchange format generation
- **Multi-currency Support**: Automatic currency detection (JPY/USD) with appropriate formatting
- **Investment Positions**: Complete position and security information embedding

# External Dependencies

## Core Libraries
- **Flask**: Web framework for application structure
- **yfinance**: Yahoo Finance API integration for stock price data
- **BeautifulSoup4**: HTML parsing for web scraping fallbacks
- **trafilatura**: Advanced content extraction for mutual fund data
- **requests**: HTTP client for API communications

## Frontend Dependencies
- **Bootstrap 5**: UI framework with dark theme support
- **Font Awesome 6**: Icon library for enhanced user interface
- **CDN Delivery**: External CDN resources for frontend assets

## Data Sources
- **Yahoo Finance**: Primary API for Japanese and US stock market data
- **Web Scraping Targets**: Backup data sources for mutual fund pricing information
- **Multiple Exchanges**: Support for Tokyo, Osaka, Nagoya, Fukuoka, and Sapporo stock exchanges

## File Format Standards
- **OFX (Open Financial Exchange)**: Industry-standard format for financial data exchange
- **Multi-timezone Support**: JST timezone handling for Japanese market data
- **Currency Standards**: ISO currency code compliance (JPY, USD)