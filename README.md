# Opensea Swap Fee Calculator

## Installation

```bash
pip install -r requirements.txt
```

## Features

* Multi-threaded wallet processing
* Proxy support for API requests
* Retry mechanism for failed requests
* Excel and JSON output formats
* Comprehensive fee analysis

## Setup

Create the following files in the project directory:

### **wallets.txt**
```
0x1234567890123456789012345678901234567890
0xabcdefabcdefabcdefabcdefabcdefabcdefabcd
```

### **proxy.txt** *(optional)*
```
log:pass@ip:port
log:pass@ip:port
```

## Usage

```bash
py main.py
```

The script will:
1. Load wallet addresses from `wallets.txt`
2. Process each wallet using multiple threads
3. Collect fee data from relay.link API
4. Generate reports with results

## Output Files

* **`relay_fees_results.xlsx`** - Excel spreadsheet with wallet summaries
* **`fees_detailed.json`** - Complete fee transaction data
* **`fees_summary.json`** - Statistical summary of results
