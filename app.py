#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

from flask import Flask, request, render_template, jsonify

# Ensure src/ is on sys.path for local execution
PROJECT_ROOT = Path(__file__).resolve().parent
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from badho_search.hybrid_search import HybridSearchEngine
from badho_search.database import ProductDatabase

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection string
CONNECTION_STRING = "postgres://postgres:Badho_1301@db.badho.in:5432/badho-app"

app = Flask(__name__)

# Initialize search engine and database
search_engine = HybridSearchEngine()
product_db = ProductDatabase(CONNECTION_STRING)

# Thread pool for async database operations
executor = ThreadPoolExecutor(max_workers=4)

class SearchFacetSystem:
    def __init__(self, search_engine: HybridSearchEngine, product_db: ProductDatabase):
        self.search_engine = search_engine
        self.product_db = product_db
    
    def search_with_facets(self, query: str, facet_filters: Dict[str, List[str]] = None, k: int = 20, only_active_facets: bool = False) -> Dict[str, Any]:
        """Perform hybrid search and return results immediately, facets will be loaded separately"""
        try:
            # Step 1: Get search results from FAISS (fastest operation)
            results, timing = self.search_engine.hybrid_search(
                query=query,
                k=k,
                phonetic_boost=0.2,
                candidate_pool=100,
                return_timing=True
            )
            
            if not results:
                return {
                    'results': [],
                    'facets': {},
                    'timing': self._timing_to_dict(timing),
                    'total_results': 0,
                    'search_complete': True,
                    'facets_loading': False
                }
            
            # Step 2: Extract brand_sku_ids directly from search results (much faster!)
            brand_sku_ids = [item.get('id', '') for item in results if item.get('id')]
            
            # Step 3: Apply facet filters if provided (synchronous for immediate filtering)
            filtered_results = results
            if facet_filters and brand_sku_ids:
                # Get products that match the facet filters directly by ID
                filtered_brand_sku_ids = self.product_db.get_brand_skus_matching_facets(facet_filters, brand_sku_ids)
                
                if filtered_brand_sku_ids:
                    # Filter search results to only include products whose brand SKUs match the facet criteria
                    filtered_results = []
                    for result in results:
                        if result.get('id') in filtered_brand_sku_ids:
                            filtered_results.append(result)
                else:
                    # No results match the filters
                    filtered_results = []
            
            # Return search results immediately
            return {
                'results': filtered_results,
                'facets': {},  # Empty initially, will be loaded separately
                'timing': self._timing_to_dict(timing),
                'total_results': len(filtered_results),
                'search_complete': True,
                'facets_loading': True,
                'brand_sku_ids': brand_sku_ids,  # For facet loading - now using IDs directly
                'facet_filters': facet_filters or {},
                'only_active_facets': only_active_facets
            }
            
        except Exception as e:
            logger.error(f"Search with facets failed: {e}")
            return {
                'results': [],
                'facets': {},
                'timing': None,
                'total_results': 0,
                'error': str(e),
                'search_complete': False,
                'facets_loading': False
            }
    
    def get_facets_async(self, brand_sku_ids: List[str], facet_filters: Dict[str, List[str]] = None, only_active_facets: bool = False) -> Dict[str, Any]:
        """Get facets asynchronously for the given brand_sku_ids - now using direct ID lookup for much faster performance"""
        try:
            if not brand_sku_ids:
                return {'facets': {}, 'facets_complete': True}
            
            # Get facets directly by brand_sku_ids - no more label matching needed!
            facets = self.product_db.get_facets_direct_by_ids(brand_sku_ids, only_active_facets)
            
            # Process facets for UI display
            processed_facets = self._process_facets_for_ui(facets)
            
            return {
                'facets': processed_facets,
                'facets_complete': True
            }
            
        except Exception as e:
            logger.error(f"Async facets loading failed: {e}")
            return {
                'facets': {},
                'facets_complete': False,
                'error': str(e)
            }
    
    def _timing_to_dict(self, timing):
        """Convert timing object to dictionary for JSON serialization"""
        if timing is None:
            return None
        return {
            'total_ms': getattr(timing, 'total_ms', 0),
            'embed_ms': getattr(timing, 'embed_ms', 0),
            'faiss_ms': getattr(timing, 'faiss_ms', 0),
            'rerank_ms': getattr(timing, 'rerank_ms', 0)
        }
    
    def _process_facets_for_ui(self, facets: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """Process facets for UI display - prioritize by price_range first, then by total product count"""
        processed = {}
        facet_totals = {}
        
        # First pass: process facets and calculate totals
        for standard_key, facet_items in facets.items():
            if standard_key == 'price_range':
                # Handle price range facets specially
                facet_options = []
                total_products = 0
                for item in facet_items:
                    count = item['count']
                    total_products += count
                    facet_options.append({
                        'value': item['facet_value'],
                        'count': count,
                        'display_name': f"{item['facet_value']} ({count})",
                        'min_price': item.get('min_price'),
                        'max_price': item.get('max_price')
                    })
                # Sort price ranges by min_price
                facet_options.sort(key=lambda x: x.get('min_price', 0))
                facet_totals[standard_key] = total_products
            else:
                # Count occurrences of each facet value for regular facets
                value_counts = {}
                for item in facet_items:
                    value = item['facet_value']
                    if value not in value_counts:
                        value_counts[value] = 0
                    value_counts[value] += 1
                
                # Create list of facet options with counts
                facet_options = []
                total_products = 0
                for value, count in value_counts.items():
                    facet_options.append({
                        'value': value,
                        'count': count,
                        'display_name': value
                    })
                    total_products += count
                
                # Sort by count descending
                facet_options.sort(key=lambda x: x['count'], reverse=True)
                facet_totals[standard_key] = total_products
            
            processed[standard_key] = facet_options
        
        # EXPLICIT ORDERING: Build result with price_range first
        ordered_result = {}
        
        # Step 1: Add price_range first if it exists
        if 'price_range' in processed:
            ordered_result['price_range'] = processed['price_range']
            logger.info("Added price_range as first facet")
        
        # Step 2: Add other facets sorted by total product count (descending)
        other_facets = []
        for key, value in processed.items():
            if key != 'price_range':
                other_facets.append((key, value, facet_totals.get(key, 0)))
        
        # Sort by total count descending
        other_facets.sort(key=lambda x: x[2], reverse=True)
        
        # Add to ordered result
        for key, value, _ in other_facets:
            ordered_result[key] = value
        
        logger.info(f"Final facet order: {list(ordered_result.keys())[:5]}...")
        return ordered_result

# Initialize the search system
search_system = SearchFacetSystem(search_engine, product_db)

@app.route('/')
def index():
    """Main search page"""
    return render_template('search.html')

@app.route('/search')
def search():
    """API endpoint for search with facets - returns results immediately, facets load separately"""
    query = request.args.get('q', '').strip()
    k = int(request.args.get('k', 50))
    only_active_facets = request.args.get('active_facets', 'false').lower() == 'true'
    
    # Parse facet filters from query parameters
    facet_filters = {}
    for key, value in request.args.items():
        if key.startswith('facet_'):
            facet_key = key[6:]  # Remove 'facet_' prefix
            values = request.args.getlist(key)
            if values:
                facet_filters[facet_key] = [v for v in values if v.strip()]
    
    if not query:
        return jsonify({
            'results': [],
            'facets': {},
            'timing': None,
            'total_results': 0,
            'error': 'No search query provided',
            'search_complete': False,
            'facets_loading': False
        })
    
    # Perform search with facets (returns results immediately)
    search_results = search_system.search_with_facets(query, facet_filters, k, only_active_facets)
    
    # Use Flask's jsonify which handles serialization properly
    return jsonify(search_results)

@app.route('/facets')
def get_facets():
    """API endpoint for fetching facets asynchronously - now using brand_sku_ids for much faster performance"""
    brand_sku_ids = request.args.getlist('brand_sku_ids')
    only_active_facets = request.args.get('active_facets', 'false').lower() == 'true'
    
    # Parse facet filters from query parameters
    facet_filters = {}
    for key, value in request.args.items():
        if key.startswith('facet_'):
            facet_key = key[6:]  # Remove 'facet_' prefix
            values = request.args.getlist(key)
            if values:
                facet_filters[facet_key] = [v for v in values if v.strip()]
    
    if not brand_sku_ids:
        return jsonify({
            'facets': {},
            'facets_complete': False,
            'error': 'No brand_sku_ids provided'
        })
    
    # Get facets asynchronously using the new ID-based approach
    facets_result = search_system.get_facets_async(brand_sku_ids, facet_filters, only_active_facets)
    
    return jsonify(facets_result)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
