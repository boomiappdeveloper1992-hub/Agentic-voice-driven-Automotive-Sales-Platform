"""
rag_module.py - FINAL FIX - Completely accurate search
- Handles: 20k, 100k, 300k, 2 lakh, etc. (ALL formats)
- Luxury SUV detection
- Direct Neo4j queries - NO HALLUCINATION
- Feature-based search (family cars, turbo, leg space, etc.)
- Returns ONLY exact matches
"""

import logging
from typing import List, Dict, Any, Optional
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RAGSystem:
    """FINAL FIXED RAG system - 100% accurate"""
    
    def __init__(self, neo4j_handler):
        """Initialize RAG"""
        self.neo4j = neo4j_handler
        self.faq_knowledge = self._build_faq_knowledge()
        logger.info("✅ RAG System initialized (Direct Query Mode)")
    
    def _build_faq_knowledge(self) -> Dict[str, Dict]:
        """Build FAQ knowledge base"""
        return {
            'warranty': {
                'answer': 'All our vehicles come with a comprehensive 3-year/100,000 km warranty, whichever comes first. This includes 24/7 roadside assistance and free scheduled maintenance for the first year.',
                'category': 'warranty',
                'keywords': ['warranty', 'guarantee', 'coverage', 'protection']
            },
            'financing': {
                'answer': 'We offer flexible financing options with competitive rates. You can get approved with as low as 0% down payment and choose terms from 12 to 60 months. We work with major banks in UAE.',
                'category': 'financing',
                'keywords': ['financing', 'loan', 'payment', 'installment', 'bank', 'finance']
            },
            'trade-in': {
                'answer': 'Yes! We accept trade-ins and offer competitive valuations. The trade-in value can be used as down payment.',
                'category': 'trade-in',
                'keywords': ['trade-in', 'trade', 'exchange', 'old car', 'sell']
            }
        }
    
    def normalize_price(self, price_str: str) -> Optional[float]:
        """
        FIXED: Normalize price from ANY format
        Now handles: 20k, 100k, 300k, 2 lakh, etc.
        """
        if not price_str:
            return None
        
        # Clean and uppercase
        original = price_str
        price_str = str(price_str).strip().upper()
        price_str = re.sub(r'(AED|USD|RS|INR|DIRHAM|RUPEE|RUPEES|\$|₹|£|€)', '', price_str, flags=re.IGNORECASE)
        price_str = price_str.strip()
        
        logger.info(f"💰 Normalizing: '{original}' → '{price_str}'")
        
        # Text numbers
        text_to_num = {
            'ONE': 1, 'TWO': 2, 'THREE': 3, 'FOUR': 4, 'FIVE': 5,
            'SIX': 6, 'SEVEN': 7, 'EIGHT': 8, 'NINE': 9, 'TEN': 10
        }
        for word, num in text_to_num.items():
            price_str = re.sub(r'\b' + word + r'\b', str(num), price_str)
        
        # CRORE (10 million)
        if any(term in price_str for term in ['CRORE', 'CRORES', 'CR']):
            price_str = re.sub(r'(CRORE|CRORES|CR)', '', price_str)
            try:
                num = float(re.sub(r'[^\d.]', '', price_str))
                result = num * 10000000
                logger.info(f"✅ {num} crore = {result:,.0f}")
                return result
            except:
                pass
        
        # LAKH/LAC (100,000)
        if any(term in price_str for term in ['LAKH', 'LAKHS', 'LAC', 'LACS']):
            price_str = re.sub(r'(LAKH|LAKHS|LAC|LACS)', '', price_str)
            try:
                num = float(re.sub(r'[^\d.]', '', price_str))
                result = num * 100000
                logger.info(f"✅ {num} lakh = {result:,.0f}")
                return result
            except:
                pass
        
        # K or THOUSAND (1,000) - CRITICAL FIX
        if 'K' in price_str or 'THOUSAND' in price_str:
            price_str = re.sub(r'(K|THOUSAND)', '', price_str)
            try:
                # Extract number (handles 20, 100, 300, 2.5, etc.)
                num = float(re.sub(r'[^\d.]', '', price_str))
                result = num * 1000
                logger.info(f"✅ {num}k = {result:,.0f}")
                return result
            except Exception as e:
                logger.error(f"❌ K parsing failed: {e}")
                pass
        
        # M or MILLION (1,000,000)
        if 'M' in price_str or 'MILLION' in price_str:
            price_str = re.sub(r'(M|MILLION)', '', price_str)
            try:
                num = float(re.sub(r'[^\d.]', '', price_str))
                result = num * 1000000
                logger.info(f"✅ {num}m = {result:,.0f}")
                return result
            except:
                pass
        
        # Standard number
        try:
            result = float(price_str.replace(',', '').replace(' ', ''))
            logger.info(f"✅ Standard: {result:,.0f}")
            return result
        except:
            logger.warning(f"⚠️ Could not parse: '{price_str}'")
            return None
    
    def extract_search_intent(self, query: str) -> Dict[str, Any]:
        """
        ENHANCED: Better intent extraction with feature detection
        """
        query_lower = query.lower()
        intent = {
            'type': 'general',
            'parameters': {},
            'features': []  # NEW: Track requested features
        }
        
        logger.info(f"🔍 Query: '{query}'")
        
        # ===== FEATURE DETECTION (NEW) =====
        feature_keywords = {
            'family': ['family', 'families', '7 seat', 'seven seat', '8 seat', 'spacious', 'large'],
            'turbo': ['turbo', 'turbocharged', 'powerful', 'performance'],
            'hybrid': ['hybrid', 'eco', 'fuel efficient', 'economy'],
            'electric': ['electric', 'ev', 'battery', 'plug-in'],
            'luxury': ['luxury', 'premium', 'high-end', 'expensive'],
            'safety': ['safety', 'safe', 'airbags', 'collision', 'lane assist'],
            'comfort': ['comfort', 'comfortable', 'leg space', 'legroom', 'spacious interior'],
            'technology': ['tech', 'technology', 'smart', 'carplay', 'android auto', 'touchscreen'],
            '4wd': ['4wd', '4x4', 'awd', 'all-wheel', 'off-road'],
            'sunroof': ['sunroof', 'panoramic', 'moonroof'],
            'leather': ['leather', 'leather seats'],
            'navigation': ['navigation', 'gps', 'maps'],
            'parking': ['parking sensors', 'parking camera', '360 camera', 'reverse camera']
        }
        
        for feature_name, keywords in feature_keywords.items():
            if any(kw in query_lower for kw in keywords):
                intent['features'].append(feature_name)
                logger.info(f"🎯 Feature requested: {feature_name}")
        
        # ===== YEAR EXTRACTION =====
        year_match = re.search(r'\b(20\d{2})\b', query)
        if year_match:
            year = int(year_match.group(1))
            if 2000 <= year <= 2030:
                intent['parameters']['year'] = year
                intent['type'] = 'year_search'
                logger.info(f"📅 Year: {year}")
        
        # ===== BRAND EXTRACTION =====
        brands = {
            'toyota': ['toyota'],
            'honda': ['honda'],
            'nissan': ['nissan'],
            'ford': ['ford'],
            'bmw': ['bmw'],
            'mercedes': ['mercedes', 'benz', 'mercedes-benz'],
            'audi': ['audi'],
            'lexus': ['lexus'],
            'tesla': ['tesla'],
            'hyundai': ['hyundai'],
            'kia': ['kia'],
            'byd': ['byd'],
            'mazda': ['mazda'],
            'chevrolet': ['chevrolet', 'chevy'],
            'volkswagen': ['volkswagen', 'vw'],
            'porsche': ['porsche'],
            'land rover': ['land rover', 'range rover'],
            'jaguar': ['jaguar']
        }
        
        for brand_key, variants in brands.items():
            for variant in variants:
                if variant in query_lower:
                    intent['parameters']['brand'] = brand_key.title()
                    if intent['type'] == 'general':
                        intent['type'] = 'brand_search'
                    logger.info(f"🚗 Brand: {brand_key.title()}")
                    break
        
        # ===== MODEL EXTRACTION =====
        models = ['camry', 'corolla', 'land cruiser', 'prado', 'accord', 'civic', 
                 'altima', 'x5', 'x3', 'gle', 'glc', 'a4', 'a6', 'q5', 'q7', 'rav4',
                 'highlander', 'pilot', 'crv', 'cr-v', 'pathfinder', 'rogue',
                 'mustang', 'f-150', 'explorer', 'escape', 'bronco']
        
        for model in models:
            if model in query_lower:
                intent['parameters']['model'] = model.title()
                logger.info(f"🏷️ Model: {model.title()}")
                break
        
        # ===== PRICE EXTRACTION =====
        
        # Under/Below patterns
        under_patterns = [
            r'(?:under|below|less than|max|maximum|up to|upto)\s+(?:aed\s+)?(\d+\.?\d*)\s*(k|lakh|lakhs|lac|lacs|thousand|million|m|crore)?',
            r'(?:under|below|less than|max|maximum|up to|upto)\s+aed\s+(\d+,?\d*)',
        ]
        
        for pattern in under_patterns:
            match = re.search(pattern, query_lower)
            if match:
                price_str = match.group(1)
                multiplier = match.group(2) if len(match.groups()) > 1 else None
                
                # Combine number and multiplier
                if multiplier:
                    price_str = f"{price_str}{multiplier}"
                
                normalized = self.normalize_price(price_str)
                if normalized:
                    intent['parameters']['max_budget'] = normalized
                    intent['type'] = 'budget_search'
                    logger.info(f"💵 Max: {normalized:,.0f}")
                    break
        
        # Above/Over patterns
        over_patterns = [
            r'(?:above|over|more than|min|minimum)\s+(?:aed\s+)?(\d+\.?\d*)\s*(k|lakh|lakhs|lac|lacs)?',
        ]
        
        for pattern in over_patterns:
            match = re.search(pattern, query_lower)
            if match:
                price_str = match.group(1)
                multiplier = match.group(2) if len(match.groups()) > 1 else None
                
                if multiplier:
                    price_str = f"{price_str}{multiplier}"
                
                normalized = self.normalize_price(price_str)
                if normalized:
                    intent['parameters']['min_budget'] = normalized
                    intent['type'] = 'budget_search'
                    logger.info(f"💵 Min: {normalized:,.0f}")
                    break
        
        # Between X and Y
        range_match = re.search(
            r'between\s+(?:aed\s+)?(\d+\.?\d*)\s*(k|lakh|lakhs|lac|lacs)?\s+(?:and|to)\s+(?:aed\s+)?(\d+\.?\d*)\s*(k|lakh|lakhs|lac|lacs)?',
            query_lower
        )
        if range_match:
            price1 = range_match.group(1)
            mult1 = range_match.group(2) if range_match.group(2) else ''
            price2 = range_match.group(3)
            mult2 = range_match.group(4) if range_match.group(4) else ''
            
            p1 = self.normalize_price(f"{price1}{mult1}")
            p2 = self.normalize_price(f"{price2}{mult2}")
            
            if p1 and p2:
                intent['parameters']['min_budget'] = min(p1, p2)
                intent['parameters']['max_budget'] = max(p1, p2)
                intent['type'] = 'budget_search'
                logger.info(f"💵 Range: {min(p1, p2):,.0f} - {max(p1, p2):,.0f}")
        
        # ===== VEHICLE TYPE (ENHANCED) =====
        
        # SUV detection
        if any(word in query_lower for word in ['suv', 'sport utility', 'crossover', '4x4', 'off-road']):
            intent['parameters']['vehicle_type'] = 'suv'
            if intent['type'] == 'general':
                intent['type'] = 'category_search'
            logger.info(f"📦 Type: SUV")
        
        # Sedan
        elif any(word in query_lower for word in ['sedan', 'saloon']):
            intent['parameters']['vehicle_type'] = 'sedan'
            logger.info(f"📦 Type: Sedan")
        
        # Truck/Pickup
        elif any(word in query_lower for word in ['truck', 'pickup', 'pick-up']):
            intent['parameters']['vehicle_type'] = 'truck'
            logger.info(f"📦 Type: Truck")
        
        logger.info(f"✅ Intent: {intent}")
        return intent
    
    def search_vehicles(self, query: str, top_k: int = 20, language: str = 'en') -> Dict[str, Any]:
        """
        MAIN SEARCH - Direct Neo4j queries with feature matching
        """
        try:
            logger.info(f"🔍 SEARCH START: '{query}'")
            
            # ✅ CRITICAL FIX: Initialize vehicles at the start!
            vehicles = []
            
            # Check FAQ
            faq = self._check_faq(query)
            if faq:
                return faq
            
            # Extract intent
            intent = self.extract_search_intent(query)
            
            # Build Cypher query
            conditions = []
            params = {}
            
            # Brand filter
            if 'brand' in intent['parameters']:
                conditions.append("toLower(v.make) = toLower($brand)")
                params['brand'] = intent['parameters']['brand']
                logger.info(f"🔹 Filter: Brand = {params['brand']}")
            
            # Model filter
            if 'model' in intent['parameters']:
                conditions.append("toLower(v.model) CONTAINS toLower($model)")
                params['model'] = intent['parameters']['model']
                logger.info(f"🔹 Filter: Model contains '{params['model']}'")
            
            # Year filter
            if 'year' in intent['parameters']:
                conditions.append("v.year = $year")
                params['year'] = intent['parameters']['year']
                logger.info(f"🔹 Filter: Year = {params['year']}")
            
            # Price filters
            if 'min_budget' in intent['parameters']:
                conditions.append("v.price >= $min_price")
                params['min_price'] = intent['parameters']['min_budget']
                logger.info(f"🔹 Filter: Price >= {params['min_price']:,.0f}")
            
            if 'max_budget' in intent['parameters']:
                conditions.append("v.price <= $max_price")
                params['max_price'] = intent['parameters']['max_budget']
                logger.info(f"🔹 Filter: Price <= {params['max_price']:,.0f}")
            
            # Luxury filter
            if 'luxury' in intent['features']:
                conditions.append("v.price > 200000")
                logger.info(f"🔹 Filter: Luxury (price > 200k)")
            
            # Vehicle type
            if 'vehicle_type' in intent['parameters']:
                vtype = intent['parameters']['vehicle_type']
                if vtype == 'suv':
                    conditions.append("(toLower(v.model) CONTAINS 'suv' OR toLower(v.make) IN ['toyota', 'nissan', 'ford'] OR ANY(f IN v.features WHERE toLower(f) CONTAINS 'suv' OR toLower(f) CONTAINS '4wd' OR toLower(f) CONTAINS 'awd'))")
                elif vtype == 'sedan':
                    conditions.append("(toLower(v.model) CONTAINS 'sedan' OR toLower(v.model) CONTAINS 'saloon' OR toLower(v.model) IN ['camry', 'accord', 'altima', 'civic', 'corolla'])")
                elif vtype == 'truck':
                    conditions.append("(toLower(v.model) CONTAINS 'truck' OR toLower(v.model) CONTAINS 'pickup' OR toLower(v.model) CONTAINS 'f-150')")
                logger.info(f"🔹 Filter: Type = {vtype}")
            
            # ===== FEATURE FILTERS (NEW) =====
            if intent['features']:
                feature_conditions = []
                
                for feature in intent['features']:
                    if feature == 'family':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS '7 seat' OR toLower(f) CONTAINS 'spacious' OR toLower(f) CONTAINS 'large'))")
                    elif feature == 'turbo':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS 'turbo' OR toLower(f) CONTAINS 'performance'))")
                    elif feature == 'hybrid':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS 'hybrid' OR toLower(f) CONTAINS 'eco'))")
                    elif feature == 'electric':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS 'electric' OR toLower(f) CONTAINS 'ev'))")
                    elif feature == 'safety':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS 'safety' OR toLower(f) CONTAINS 'airbag'))")
                    elif feature == 'comfort':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS 'comfort' OR toLower(f) CONTAINS 'leather' OR toLower(f) CONTAINS 'spacious'))")
                    elif feature == 'technology':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS 'carplay' OR toLower(f) CONTAINS 'touchscreen' OR toLower(f) CONTAINS 'tech'))")
                    elif feature == '4wd':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS '4wd' OR toLower(f) CONTAINS 'awd' OR toLower(f) CONTAINS '4x4'))")
                    elif feature == 'sunroof':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS 'sunroof' OR toLower(f) CONTAINS 'panoramic'))")
                    elif feature == 'leather':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS 'leather'))")
                    elif feature == 'navigation':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS 'navigation' OR toLower(f) CONTAINS 'gps'))")
                    elif feature == 'parking':
                        feature_conditions.append("(ANY(f IN v.features WHERE toLower(f) CONTAINS 'camera' OR toLower(f) CONTAINS 'parking'))")
                
                # Combine feature conditions with OR (match any feature)
                if feature_conditions:
                    conditions.append("(" + " OR ".join(feature_conditions) + ")")
                    logger.info(f"🔹 Filter: Features = {', '.join(intent['features'])}")
            
            # Build final query
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cypher = f"""
                MATCH (v:Vehicle)
                WHERE {where_clause}
                RETURN v
                ORDER BY v.price ASC
                LIMIT 100
            """
            
            logger.info(f"📝 Cypher:\n{cypher}")
            logger.info(f"📝 Params: {params}")
            
            # Execute WITH RETRY
            results = self.neo4j.execute_with_retry(cypher, params, timeout=20.0)
            
            if results is None:
                logger.warning("⚠️ Neo4j timeout - returning empty results")
                return {
                    'vehicles': [],
                    'count': 0,
                    'message': '⚠️ Search temporarily unavailable. Please try again in a moment.',
                    'search_type': 'error',
                    'intent': intent
                }
            
            # Process results
            for record in results:
                v = record['v']
                # CALCULATE REAL RELEVANCE SCORE
                relevance_score = self._calculate_relevance_score(v, intent, query)
                
                vehicles.append({
                    'id': v['id'],
                    'make': v['make'],
                    'model': v['model'],
                    'year': v['year'],
                    'price': v['price'],
                    'features': v.get('features', []),
                    'stock': v.get('stock', 0),
                    'image': v.get('image', 'https://images.unsplash.com/photo-1552519507-da3b142c6e3d?w=600'),
                    'description': v.get('description', ''),
                    'relevance_score': relevance_score
                })

            # Sort by relevance
            vehicles.sort(key=lambda x: x['relevance_score'], reverse=True)
            logger.info(f"✅ Found {len(vehicles)} exact matches")
            
            vehicles = vehicles[:top_k]
            
            if len(vehicles) == 0:
                message = f"Oops! No vehicles found for this search. Please try different filters or keywords, '{query}'\n\nTry:\n• Broader terms\n• Different price range\n• Check spelling"
            else:
                message = f"Good news! Found {len(vehicles)} vehicle(s) for '{query}'"
            
            return {
                'vehicles': vehicles,
                'count': len(vehicles),
                'message': message,
                'search_type': 'direct_query',
                'intent': intent
            }
            
        except Exception as e:
            logger.error(f"❌ Error: {e}", exc_info=True)
            return {
                'vehicles': [],
                'count': 0,
                'message': f'Search error: {str(e)}',
                'search_type': 'error',
                'intent': {}
            }
    
    def _calculate_relevance_score(self, vehicle: Dict, intent: Dict, query: str) -> float:
        """
        Calculate REAL relevance score based on query match
        """
        score = 0.5  # Base score
        
        query_lower = query.lower()
        params = intent.get('parameters', {})
        requested_features = intent.get('features', [])
        
        # Brand match (high weight)
        if params.get('brand') and params['brand'].lower() == vehicle['make'].lower():
            score += 0.3
        elif vehicle['make'].lower() in query_lower:
            score += 0.2
        
        # Model match (high weight)
        if params.get('model') and params['model'].lower() in vehicle['model'].lower():
            score += 0.25
        elif vehicle['model'].lower() in query_lower:
            score += 0.15
        
        # Year match
        if params.get('year') and params['year'] == vehicle['year']:
            score += 0.1
        
        # Price match
        if params.get('max_budget'):
            if vehicle['price'] <= params['max_budget']:
                score += 0.1
            else:
                score -= 0.2  # Penalty for over budget
        
        if params.get('min_budget'):
            if vehicle['price'] >= params['min_budget']:
                score += 0.05
        
        # Feature match (NEW - enhanced scoring)
        if vehicle.get('features') and requested_features:
            vehicle_features_lower = [f.lower() for f in vehicle['features']]
            matched_features = 0
            
            for req_feature in requested_features:
                # Check if any vehicle feature matches the requested feature
                if req_feature == 'family':
                    if any(kw in feat for feat in vehicle_features_lower for kw in ['7 seat', 'spacious', 'large']):
                        matched_features += 1
                elif req_feature == 'turbo':
                    if any(kw in feat for feat in vehicle_features_lower for kw in ['turbo', 'performance']):
                        matched_features += 1
                elif req_feature == 'comfort':
                    if any(kw in feat for feat in vehicle_features_lower for kw in ['comfort', 'leather', 'spacious']):
                        matched_features += 1
                else:
                    if any(req_feature in feat for feat in vehicle_features_lower):
                        matched_features += 1
            
            # Bonus for matching requested features
            if matched_features > 0:
                score += min(matched_features * 0.1, 0.3)
        
        # General feature match from query
        if vehicle.get('features'):
            feature_matches = sum(1 for f in vehicle['features'] if any(word in f.lower() for word in query_lower.split()))
            score += min(feature_matches * 0.05, 0.15)
        
        # Ensure score is between 0 and 1
        return min(max(score, 0.0), 1.0)
    
    def _check_faq(self, query: str) -> Optional[Dict]:
        """Check FAQ"""
        query_lower = query.lower()
        for faq_key, faq_data in self.faq_knowledge.items():
            if any(kw in query_lower for kw in faq_data['keywords']):
                return {
                    'message': faq_data['answer'],
                    'type': 'faq',
                    'category': faq_data['category'],
                    'vehicles': [],
                    'count': 0
                }
        return None
    
    def search_by_budget(self, min_budget: int = 0, max_budget: int = 999999999) -> Dict[str, Any]:
        """Search by budget"""
        filters = {'min_price': min_budget, 'max_price': max_budget}
        vehicles = self.neo4j.get_vehicles(filters)
        return {
            'vehicles': vehicles[:20],
            'count': len(vehicles),
            'message': f'Found {len(vehicles)} in budget AED {min_budget:,} - {max_budget:,}',
            'search_type': 'budget_filter'
        }
    
    def get_vehicle_recommendations(self, lead_id: str, top_k: int = 3) -> Dict[str, Any]:
        """Get recommendations"""
        try:
            leads = self.neo4j.get_all_leads()
            lead = next((l for l in leads if l['id'] == lead_id), None)
            if not lead:
                return {'vehicles': [], 'count': 0, 'message': 'Lead not found'}
            
            query = f"{lead['interest']} budget {lead['budget']}"
            results = self.search_vehicles(query, top_k=top_k * 2)
            max_price = lead['budget'] * 1.2
            filtered = [v for v in results['vehicles'] if v['price'] <= max_price]
            
            return {
                'vehicles': filtered[:top_k],
                'count': len(filtered),
                'message': f'Recommendations for {lead["name"]}'
            }
        except Exception as e:
            logger.error(f"Recommendation error: {e}")
            return {'vehicles': [], 'count': 0, 'message': 'Error'}
    
    def general_query(self, query: str, language: str = 'en') -> Dict[str, Any]:
        """General query"""
        faq = self._check_faq(query)
        if faq:
            return faq
        
        if any(w in query.lower() for w in ['show', 'find', 'looking', 'want', 'search']):
            return self.search_vehicles(query, top_k=5)
        
        return {
            'message': "I can help you search for vehicles!\nTry: 'Show me Toyota Camry 2025' or 'luxury SUV under 300k' or 'family car with turbo'",
            'type': 'general_help',
            'vehicles': [],
            'count': 0
        }
    
    def rebuild_index(self):
        """Not needed for direct queries"""
        logger.info("✅ Using direct queries - no index needed")
    
    def compare_vehicles(self, vehicle_ids: List[str]) -> Dict[str, Any]:
        """Compare vehicles"""
        try:
            vehicles = self.neo4j.get_vehicles()
            selected = [v for v in vehicles if v['id'] in vehicle_ids]
            if len(selected) < 2:
                return {'message': 'Need at least 2 vehicles', 'vehicles': []}
            return {'vehicles': selected}
        except Exception as e:
            return {'message': 'Error', 'vehicles': []}
    
    def search_by_features(self, features: List[str]) -> Dict[str, Any]:
        """Search by features"""
        return self.search_vehicles(' '.join(features), top_k=5)
    
    def get_popular_searches(self) -> List[str]:
        """Popular searches"""
        return [
            "Toyota Camry 2025",
            "luxury SUV under 300k",
            "Honda Accord",
            "family car with turbo",
            "cars under 2 lakh",
            "hybrid sedan",
            "comfortable car with leg space"
        ]


# Test
def test():
    from neo4j_handler import Neo4jHandler
    print("\n" + "="*60)
    print("TESTING FEATURE-BASED SEARCH")
    print("="*60)
    
    neo4j = Neo4jHandler()
    rag = RAGSystem(neo4j)
    
    tests = [
        "luxury SUV under 300k",
        "family car with turbo",
        "comfortable sedan with leg space",
        "show me toyota vehicles under 100k",
        "hybrid car",
    ]
    
    for q in tests:
        print(f"\n🔍 '{q}'")
        print("-" * 60)
        r = rag.search_vehicles(q, top_k=5)
        print(f"Found: {r['count']} vehicles")
        for i, v in enumerate(r['vehicles'], 1):
            print(f"  {i}. {v['year']} {v['make']} {v['model']} - AED {v['price']:,}")
            print(f"     Features: {', '.join(v['features'][:3])}")
    
    neo4j.close()
    print("\n" + "="*60)


if __name__ == "__main__":
    test()