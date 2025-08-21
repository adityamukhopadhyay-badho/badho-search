from __future__ import annotations

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._connection = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self._connection = psycopg2.connect(
                self.connection_string,
                cursor_factory=RealDictCursor
            )
            return self._connection
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute a query and return results"""
        if not self._connection:
            self.connect()
        
        try:
            with self._connection.cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

class ProductDatabase:
    def __init__(self, connection_string: str):
        self.db = DatabaseConnection(connection_string)
    
    def get_brand_sku_by_product_names(self, product_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """Get brandSKU information for given product names"""
        if not product_names:
            return {}
        
        query = """
        SELECT 
            bs.id as brand_sku_id,
            bs.label as brand_sku_label,
            bs."brandId" as brand_id,
            bs."brandLabel" as brand_name,
            bs.label as product_name
        FROM brands."brandSKU" bs
        WHERE EXISTS (
            SELECT 1 FROM unnest(%s::text[]) AS search_term
            WHERE LOWER(bs.label) = LOWER(search_term)
        )
        """
        
        try:
            results = self.db.execute_query(query, (product_names,))
            # Create mapping from original search terms to brand_sku info
            mapping = {}
            for row in results:
                db_product_name = row['product_name']
                # Find the original search term that matches this database result
                for search_term in product_names:
                    if db_product_name.lower() == search_term.lower():
                        if search_term not in mapping:
                            mapping[search_term] = []
                        mapping[search_term].append(dict(row))
                        break
            return mapping
        except Exception as e:
            logger.error(f"Failed to get brandSKU data: {e}")
            return {}
    
    def get_facets_by_brand_sku_ids(self, brand_sku_ids: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Get facets for given brandSKU IDs"""
        if not brand_sku_ids:
            return {}
        
        query = """
        SELECT 
            bsf."brandSKUId" as brand_sku_id,
            bsf."standardKey" as standard_key,
            COALESCE(bsf."standardValue", bsf.value) as facet_value,
            bsf.value as original_value,
            bsf."standardValue" as standard_value
        FROM brands."brandSKUFacet" bsf
        WHERE bsf."brandSKUId" = ANY(%s)
        AND bsf."standardKey" IS NOT NULL
        AND bsf."isActive" = true
        ORDER BY bsf."standardKey", facet_value
        """
        
        try:
            results = self.db.execute_query(query, (brand_sku_ids,))
            # Group by standard_key
            facets = {}
            for row in results:
                key = row['standard_key']
                if key not in facets:
                    facets[key] = []
                facets[key].append(dict(row))
            return facets
        except Exception as e:
            logger.error(f"Failed to get facets data: {e}")
            return {}
    
    def get_filtered_products(self, facet_filters: Dict[str, List[str]], product_names: List[str] = None) -> List[str]:
        """Get product names that match the given facet filters"""
        if not facet_filters:
            return product_names or []
        
        conditions = []
        params = []
        
        for standard_key, values in facet_filters.items():
            if values:  # Only add condition if values list is not empty
                conditions.append(f"""
                    EXISTS (
                        SELECT 1 FROM brands."brandSKUFacet" bsf2 
                        WHERE bsf2."brandSKUId" = bs.id 
                        AND bsf2."standardKey" = %s 
                        AND COALESCE(bsf2."standardValue", bsf2.value) = ANY(%s)
                        AND bsf2."isActive" = true
                    )
                """)
                params.append(standard_key)
                params.append(values)
        
        if not conditions:
            return product_names or []
        
        base_query = """
        SELECT DISTINCT bs.label as product_name
        FROM brands."brandSKU" bs
        """
        
        if product_names:
            base_query += " WHERE bs.label = ANY(%s)"
            params.insert(0, product_names)
            where_clause = " AND " + " AND ".join(conditions)
        else:
            where_clause = " WHERE " + " AND ".join(conditions)
        
        query = base_query + where_clause
        
        try:
            results = self.db.execute_query(query, tuple(params))
            return [row['product_name'] for row in results]
        except Exception as e:
            logger.error(f"Failed to filter products: {e}")
            return []
    
    def get_brand_skus_matching_facets(self, facet_filters: Dict[str, List[str]], brand_sku_ids: List[str]) -> List[str]:
        """Get brand SKU IDs that match the given facet filters from a specific set of brand SKU IDs"""
        if not facet_filters or not brand_sku_ids:
            return brand_sku_ids
        
        conditions = []
        params = [brand_sku_ids]  # First parameter is the brand SKU IDs list
        
        for standard_key, values in facet_filters.items():
            if values:  # Only add condition if values list is not empty
                conditions.append(f"""
                    EXISTS (
                        SELECT 1 FROM brands."brandSKUFacet" bsf2 
                        WHERE bsf2."brandSKUId" = bs.id 
                        AND bsf2."standardKey" = %s 
                        AND COALESCE(bsf2."standardValue", bsf2.value) = ANY(%s)
                        AND bsf2."isActive" = true
                    )
                """)
                params.append(standard_key)
                params.append(values)
        
        if not conditions:
            return brand_sku_ids
        
        query = """
        SELECT DISTINCT bs.id
        FROM brands."brandSKU" bs
        WHERE bs.id = ANY(%s)
        """ + " AND " + " AND ".join(conditions)
        
        try:
            results = self.db.execute_query(query, tuple(params))
            return [row['id'] for row in results]
        except Exception as e:
            logger.error(f"Failed to filter brand SKUs by facets: {e}")
            return []
    
    def close(self):
        """Close database connection"""
        self.db.close()
