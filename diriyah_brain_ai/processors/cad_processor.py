"""
Advanced CAD Processing Module for Diriyah Brain AI
Handles DXF, DWG, and other CAD file formats for quantity extraction and analysis
"""
import os
import logging
import json
from typing import Dict, List, Any, Optional, Tuple
import ezdxf
from ezdxf import recover
import math
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class CADProcessor:
    """Advanced CAD file processor for construction project analysis"""
    
    def __init__(self):
        self.supported_formats = ['.dxf', '.dwg']
        self.construction_layers = {
            'structural': ['STRUCT', 'BEAM', 'COLUMN', 'SLAB', 'FOUNDATION', 'WALL'],
            'architectural': ['ARCH', 'DOOR', 'WINDOW', 'ROOM', 'FURNITURE'],
            'mechanical': ['MECH', 'HVAC', 'PIPE', 'DUCT', 'EQUIPMENT'],
            'electrical': ['ELEC', 'LIGHT', 'POWER', 'CABLE', 'PANEL'],
            'plumbing': ['PLUMB', 'WATER', 'DRAIN', 'FIXTURE'],
            'landscape': ['LAND', 'TREE', 'PLANT', 'PAVING', 'IRRIGATION']
        }
        
        self.material_keywords = {
            'concrete': ['CONC', 'CONCRETE', 'C25', 'C30', 'C35', 'C40'],
            'steel': ['STEEL', 'REBAR', 'REINF', 'ST37', 'ST52'],
            'masonry': ['BRICK', 'BLOCK', 'MASON', 'CMU'],
            'timber': ['WOOD', 'TIMBER', 'LUMBER'],
            'aluminum': ['ALUM', 'AL'],
            'glass': ['GLASS', 'GLAZING'],
            'insulation': ['INSUL', 'THERMAL']
        }
        
    def process_cad_file(self, file_path: str, project_context: Dict = None) -> Dict[str, Any]:
        """
        Process CAD file and extract construction-relevant information
        
        Args:
            file_path: Path to CAD file
            project_context: Additional project information for context
            
        Returns:
            Dictionary containing extracted CAD data and analysis
        """
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext not in self.supported_formats:
                raise ValueError(f"Unsupported CAD format: {file_ext}")
            
            logger.info(f"Processing CAD file: {file_path}")
            
            # Load DXF file
            if file_ext == '.dxf':
                doc = self._load_dxf_file(file_path)
            else:
                # For DWG files, would need additional libraries like ODA File Converter
                logger.warning(f"DWG processing not fully implemented, treating as DXF")
                doc = self._load_dxf_file(file_path)
            
            # Extract comprehensive data
            analysis_result = {
                'file_info': self._extract_file_info(file_path, doc),
                'layers': self._analyze_layers(doc),
                'entities': self._extract_entities(doc),
                'dimensions': self._extract_dimensions(doc),
                'text_annotations': self._extract_text_annotations(doc),
                'blocks': self._analyze_blocks(doc),
                'quantities': self._calculate_quantities(doc),
                'materials': self._identify_materials(doc),
                'construction_elements': self._identify_construction_elements(doc),
                'spatial_analysis': self._perform_spatial_analysis(doc),
                'compliance_check': self._check_drawing_compliance(doc, project_context),
                'metadata': self._extract_metadata(doc),
                'processing_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"CAD processing completed successfully for {file_path}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error processing CAD file {file_path}: {str(e)}")
            return {
                'error': str(e),
                'file_path': file_path,
                'processing_timestamp': datetime.now().isoformat()
            }
    
    def _load_dxf_file(self, file_path: str):
        """Load DXF file with error recovery"""
        try:
            # Try normal loading first
            doc = ezdxf.readfile(file_path)
            logger.info(f"DXF file loaded successfully: {file_path}")
            return doc
        except ezdxf.DXFStructureError:
            # Try recovery mode for corrupted files
            logger.warning(f"DXF file corrupted, attempting recovery: {file_path}")
            doc, auditor = recover.readfile(file_path)
            if auditor.has_errors:
                logger.warning(f"DXF recovery completed with {len(auditor.errors)} errors")
            return doc
    
    def _extract_file_info(self, file_path: str, doc) -> Dict[str, Any]:
        """Extract basic file information"""
        file_stats = os.stat(file_path)
        
        return {
            'filename': os.path.basename(file_path),
            'file_size': file_stats.st_size,
            'creation_time': datetime.fromtimestamp(file_stats.st_ctime).isoformat(),
            'modification_time': datetime.fromtimestamp(file_stats.st_mtime).isoformat(),
            'dxf_version': doc.dxfversion if hasattr(doc, 'dxfversion') else 'Unknown',
            'units': self._detect_drawing_units(doc),
            'drawing_limits': self._get_drawing_limits(doc)
        }
    
    def _analyze_layers(self, doc) -> Dict[str, Any]:
        """Analyze layer structure and categorize by construction discipline"""
        layers_info = {}
        discipline_summary = {discipline: [] for discipline in self.construction_layers.keys()}
        
        for layer in doc.layers:
            layer_name = layer.dxf.name.upper()
            layer_info = {
                'name': layer.dxf.name,
                'color': layer.dxf.color,
                'linetype': layer.dxf.linetype,
                'lineweight': getattr(layer.dxf, 'lineweight', None),
                'frozen': layer.is_frozen(),
                'locked': layer.is_locked(),
                'entity_count': len(list(doc.modelspace().query(f'*[layer=="{layer.dxf.name}"]')))
            }
            
            # Categorize by construction discipline
            discipline = self._categorize_layer(layer_name)
            layer_info['discipline'] = discipline
            
            if discipline != 'unknown':
                discipline_summary[discipline].append(layer.dxf.name)
            
            layers_info[layer.dxf.name] = layer_info
        
        return {
            'layers': layers_info,
            'discipline_summary': discipline_summary,
            'total_layers': len(layers_info)
        }
    
    def _categorize_layer(self, layer_name: str) -> str:
        """Categorize layer by construction discipline"""
        layer_upper = layer_name.upper()
        
        for discipline, keywords in self.construction_layers.items():
            for keyword in keywords:
                if keyword in layer_upper:
                    return discipline
        
        return 'unknown'
    
    def _extract_entities(self, doc) -> Dict[str, Any]:
        """Extract and analyze drawing entities"""
        entity_summary = {}
        geometric_data = []
        
        msp = doc.modelspace()
        
        for entity in msp:
            entity_type = entity.dxftype()
            
            if entity_type not in entity_summary:
                entity_summary[entity_type] = 0
            entity_summary[entity_type] += 1
            
            # Extract geometric data for key entity types
            if entity_type in ['LINE', 'POLYLINE', 'LWPOLYLINE', 'CIRCLE', 'ARC', 'RECTANGLE']:
                geom_data = self._extract_geometric_data(entity)
                if geom_data:
                    geometric_data.append(geom_data)
        
        return {
            'entity_summary': entity_summary,
            'total_entities': sum(entity_summary.values()),
            'geometric_data': geometric_data[:100]  # Limit to first 100 for performance
        }
    
    def _extract_geometric_data(self, entity) -> Optional[Dict[str, Any]]:
        """Extract geometric properties from entity"""
        try:
            entity_type = entity.dxftype()
            data = {
                'type': entity_type,
                'layer': entity.dxf.layer,
                'color': entity.dxf.color
            }
            
            if entity_type == 'LINE':
                data.update({
                    'start_point': list(entity.dxf.start),
                    'end_point': list(entity.dxf.end),
                    'length': entity.dxf.start.distance(entity.dxf.end)
                })
            
            elif entity_type == 'CIRCLE':
                data.update({
                    'center': list(entity.dxf.center),
                    'radius': entity.dxf.radius,
                    'area': math.pi * entity.dxf.radius ** 2,
                    'circumference': 2 * math.pi * entity.dxf.radius
                })
            
            elif entity_type in ['POLYLINE', 'LWPOLYLINE']:
                points = list(entity.get_points())
                data.update({
                    'points': points[:10],  # Limit points for performance
                    'point_count': len(points),
                    'is_closed': entity.is_closed
                })
                
                # Calculate approximate length for polylines
                if len(points) > 1:
                    total_length = 0
                    for i in range(len(points) - 1):
                        p1, p2 = points[i], points[i + 1]
                        total_length += math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                    data['length'] = total_length
            
            return data
            
        except Exception as e:
            logger.warning(f"Error extracting geometric data from {entity.dxftype()}: {str(e)}")
            return None
    
    def _extract_dimensions(self, doc) -> Dict[str, Any]:
        """Extract dimension entities and measurements"""
        dimensions = []
        dimension_summary = {}
        
        msp = doc.modelspace()
        
        for entity in msp.query('DIMENSION'):
            try:
                dim_data = {
                    'type': entity.dxftype(),
                    'layer': entity.dxf.layer,
                    'measurement': getattr(entity.dxf, 'measurement', None),
                    'text': getattr(entity.dxf, 'text', ''),
                    'style': getattr(entity.dxf, 'dimstyle', 'STANDARD')
                }
                
                dimensions.append(dim_data)
                
                dim_type = entity.dxftype()
                if dim_type not in dimension_summary:
                    dimension_summary[dim_type] = 0
                dimension_summary[dim_type] += 1
                
            except Exception as e:
                logger.warning(f"Error processing dimension entity: {str(e)}")
        
        return {
            'dimensions': dimensions,
            'dimension_summary': dimension_summary,
            'total_dimensions': len(dimensions)
        }
    
    def _extract_text_annotations(self, doc) -> Dict[str, Any]:
        """Extract text entities and annotations"""
        text_entities = []
        text_summary = {}
        
        msp = doc.modelspace()
        
        for entity in msp.query('TEXT MTEXT'):
            try:
                text_data = {
                    'type': entity.dxftype(),
                    'layer': entity.dxf.layer,
                    'text': entity.dxf.text if hasattr(entity.dxf, 'text') else '',
                    'height': getattr(entity.dxf, 'height', 0),
                    'style': getattr(entity.dxf, 'style', 'STANDARD'),
                    'position': list(getattr(entity.dxf, 'insert', [0, 0, 0]))
                }
                
                text_entities.append(text_data)
                
                # Categorize text content
                text_content = text_data['text'].upper()
                category = self._categorize_text_content(text_content)
                
                if category not in text_summary:
                    text_summary[category] = 0
                text_summary[category] += 1
                
            except Exception as e:
                logger.warning(f"Error processing text entity: {str(e)}")
        
        return {
            'text_entities': text_entities[:50],  # Limit for performance
            'text_summary': text_summary,
            'total_text_entities': len(text_entities)
        }
    
    def _categorize_text_content(self, text: str) -> str:
        """Categorize text content by construction context"""
        text_upper = text.upper()
        
        if any(keyword in text_upper for keyword in ['ROOM', 'SPACE', 'AREA']):
            return 'room_labels'
        elif any(keyword in text_upper for keyword in ['DIM', 'MM', 'CM', 'M', 'FT', 'IN']):
            return 'dimensions'
        elif any(keyword in text_upper for keyword in ['CONC', 'STEEL', 'BRICK']):
            return 'materials'
        elif any(keyword in text_upper for keyword in ['LEVEL', 'ELEV', 'RL']):
            return 'elevations'
        elif any(keyword in text_upper for keyword in ['GRID', 'AXIS']):
            return 'grid_references'
        elif any(keyword in text_upper for keyword in ['NOTE', 'SPEC', 'DETAIL']):
            return 'specifications'
        else:
            return 'general'
    
    def _analyze_blocks(self, doc) -> Dict[str, Any]:
        """Analyze block definitions and insertions"""
        blocks_info = {}
        block_insertions = {}
        
        # Analyze block definitions
        for block_name, block_def in doc.blocks.items():
            if not block_name.startswith('*'):  # Skip anonymous blocks
                entity_count = len(list(block_def))
                blocks_info[block_name] = {
                    'name': block_name,
                    'entity_count': entity_count,
                    'category': self._categorize_block(block_name)
                }
        
        # Count block insertions
        msp = doc.modelspace()
        for insert in msp.query('INSERT'):
            block_name = insert.dxf.name
            if block_name not in block_insertions:
                block_insertions[block_name] = 0
            block_insertions[block_name] += 1
        
        return {
            'block_definitions': blocks_info,
            'block_insertions': block_insertions,
            'total_blocks': len(blocks_info),
            'total_insertions': sum(block_insertions.values())
        }
    
    def _categorize_block(self, block_name: str) -> str:
        """Categorize block by construction element type"""
        name_upper = block_name.upper()
        
        if any(keyword in name_upper for keyword in ['DOOR', 'DR']):
            return 'doors'
        elif any(keyword in name_upper for keyword in ['WINDOW', 'WIN', 'WD']):
            return 'windows'
        elif any(keyword in name_upper for keyword in ['FIXTURE', 'TOILET', 'SINK']):
            return 'fixtures'
        elif any(keyword in name_upper for keyword in ['FURNITURE', 'CHAIR', 'TABLE']):
            return 'furniture'
        elif any(keyword in name_upper for keyword in ['EQUIPMENT', 'MECH', 'ELEC']):
            return 'equipment'
        elif any(keyword in name_upper for keyword in ['SYMBOL', 'SYM']):
            return 'symbols'
        else:
            return 'general'
    
    def _calculate_quantities(self, doc) -> Dict[str, Any]:
        """Calculate construction quantities from CAD entities"""
        quantities = {
            'areas': {},
            'lengths': {},
            'counts': {},
            'volumes': {}
        }
        
        msp = doc.modelspace()
        
        # Calculate areas from closed polylines and circles
        for entity in msp.query('LWPOLYLINE POLYLINE CIRCLE'):
            layer = entity.dxf.layer
            layer_category = self._categorize_layer(layer.upper())
            
            if layer_category not in quantities['areas']:
                quantities['areas'][layer_category] = 0
            
            try:
                if entity.dxftype() == 'CIRCLE':
                    area = math.pi * entity.dxf.radius ** 2
                    quantities['areas'][layer_category] += area
                elif entity.is_closed:
                    # Approximate area calculation for closed polylines
                    points = list(entity.get_points())
                    if len(points) > 2:
                        area = self._calculate_polygon_area(points)
                        quantities['areas'][layer_category] += area
            except Exception as e:
                logger.warning(f"Error calculating area for entity: {str(e)}")
        
        # Calculate lengths from lines and open polylines
        for entity in msp.query('LINE LWPOLYLINE POLYLINE ARC'):
            layer = entity.dxf.layer
            layer_category = self._categorize_layer(layer.upper())
            
            if layer_category not in quantities['lengths']:
                quantities['lengths'][layer_category] = 0
            
            try:
                if entity.dxftype() == 'LINE':
                    length = entity.dxf.start.distance(entity.dxf.end)
                    quantities['lengths'][layer_category] += length
                elif entity.dxftype() in ['LWPOLYLINE', 'POLYLINE']:
                    points = list(entity.get_points())
                    if len(points) > 1:
                        total_length = 0
                        for i in range(len(points) - 1):
                            p1, p2 = points[i], points[i + 1]
                            total_length += math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                        quantities['lengths'][layer_category] += total_length
            except Exception as e:
                logger.warning(f"Error calculating length for entity: {str(e)}")
        
        # Count block insertions by category
        for insert in msp.query('INSERT'):
            block_name = insert.dxf.name
            block_category = self._categorize_block(block_name)
            
            if block_category not in quantities['counts']:
                quantities['counts'][block_category] = 0
            quantities['counts'][block_category] += 1
        
        return quantities
    
    def _calculate_polygon_area(self, points: List[Tuple[float, float]]) -> float:
        """Calculate area of polygon using shoelace formula"""
        if len(points) < 3:
            return 0
        
        area = 0
        n = len(points)
        
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        return abs(area) / 2
    
    def _identify_materials(self, doc) -> Dict[str, Any]:
        """Identify materials from layer names and text annotations"""
        materials_found = {}
        
        # Check layer names for material keywords
        for layer in doc.layers:
            layer_name = layer.dxf.name.upper()
            for material, keywords in self.material_keywords.items():
                if any(keyword in layer_name for keyword in keywords):
                    if material not in materials_found:
                        materials_found[material] = {'layers': [], 'text_references': []}
                    materials_found[material]['layers'].append(layer.dxf.name)
        
        # Check text annotations for material specifications
        msp = doc.modelspace()
        for entity in msp.query('TEXT MTEXT'):
            try:
                text_content = entity.dxf.text.upper() if hasattr(entity.dxf, 'text') else ''
                for material, keywords in self.material_keywords.items():
                    if any(keyword in text_content for keyword in keywords):
                        if material not in materials_found:
                            materials_found[material] = {'layers': [], 'text_references': []}
                        materials_found[material]['text_references'].append(text_content[:100])
            except Exception as e:
                logger.warning(f"Error processing text for material identification: {str(e)}")
        
        return materials_found
    
    def _identify_construction_elements(self, doc) -> Dict[str, Any]:
        """Identify specific construction elements and their properties"""
        elements = {
            'structural_elements': [],
            'architectural_elements': [],
            'mep_elements': [],
            'site_elements': []
        }
        
        # Analyze by layers and blocks
        for layer in doc.layers:
            layer_name = layer.dxf.name.upper()
            discipline = self._categorize_layer(layer_name)
            
            element_info = {
                'name': layer.dxf.name,
                'discipline': discipline,
                'entity_count': len(list(doc.modelspace().query(f'*[layer=="{layer.dxf.name}"]')))
            }
            
            if discipline == 'structural':
                elements['structural_elements'].append(element_info)
            elif discipline == 'architectural':
                elements['architectural_elements'].append(element_info)
            elif discipline in ['mechanical', 'electrical', 'plumbing']:
                elements['mep_elements'].append(element_info)
            elif discipline == 'landscape':
                elements['site_elements'].append(element_info)
        
        return elements
    
    def _perform_spatial_analysis(self, doc) -> Dict[str, Any]:
        """Perform spatial analysis of the drawing"""
        msp = doc.modelspace()
        
        # Calculate drawing extents
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        entity_count = 0
        for entity in msp:
            try:
                if hasattr(entity, 'dxf'):
                    if hasattr(entity.dxf, 'start') and hasattr(entity.dxf, 'end'):
                        # Line entity
                        min_x = min(min_x, entity.dxf.start.x, entity.dxf.end.x)
                        max_x = max(max_x, entity.dxf.start.x, entity.dxf.end.x)
                        min_y = min(min_y, entity.dxf.start.y, entity.dxf.end.y)
                        max_y = max(max_y, entity.dxf.start.y, entity.dxf.end.y)
                    elif hasattr(entity.dxf, 'center'):
                        # Circle or arc entity
                        radius = getattr(entity.dxf, 'radius', 0)
                        min_x = min(min_x, entity.dxf.center.x - radius)
                        max_x = max(max_x, entity.dxf.center.x + radius)
                        min_y = min(min_y, entity.dxf.center.y - radius)
                        max_y = max(max_y, entity.dxf.center.y + radius)
                    elif hasattr(entity.dxf, 'insert'):
                        # Insert or text entity
                        min_x = min(min_x, entity.dxf.insert.x)
                        max_x = max(max_x, entity.dxf.insert.x)
                        min_y = min(min_y, entity.dxf.insert.y)
                        max_y = max(max_y, entity.dxf.insert.y)
                
                entity_count += 1
            except Exception as e:
                logger.warning(f"Error in spatial analysis for entity: {str(e)}")
        
        drawing_width = max_x - min_x if max_x != float('-inf') else 0
        drawing_height = max_y - min_y if max_y != float('-inf') else 0
        
        return {
            'extents': {
                'min_x': min_x if min_x != float('inf') else 0,
                'min_y': min_y if min_y != float('inf') else 0,
                'max_x': max_x if max_x != float('-inf') else 0,
                'max_y': max_y if max_y != float('-inf') else 0
            },
            'dimensions': {
                'width': drawing_width,
                'height': drawing_height,
                'area': drawing_width * drawing_height
            },
            'entity_density': entity_count / (drawing_width * drawing_height) if drawing_width * drawing_height > 0 else 0,
            'total_entities_analyzed': entity_count
        }
    
    def _check_drawing_compliance(self, doc, project_context: Dict = None) -> Dict[str, Any]:
        """Check drawing compliance with standards and project requirements"""
        compliance_issues = []
        compliance_score = 100
        
        # Check for required layers
        required_layers = ['0']  # Layer 0 should always exist
        existing_layers = [layer.dxf.name for layer in doc.layers]
        
        for req_layer in required_layers:
            if req_layer not in existing_layers:
                compliance_issues.append(f"Missing required layer: {req_layer}")
                compliance_score -= 10
        
        # Check for drawing scale and units
        units = self._detect_drawing_units(doc)
        if units == 'unknown':
            compliance_issues.append("Drawing units not clearly defined")
            compliance_score -= 5
        
        # Check for title block (look for text in specific areas)
        msp = doc.modelspace()
        title_block_found = False
        
        for entity in msp.query('TEXT MTEXT'):
            try:
                text_content = entity.dxf.text.upper() if hasattr(entity.dxf, 'text') else ''
                if any(keyword in text_content for keyword in ['TITLE', 'PROJECT', 'DRAWING', 'SCALE']):
                    title_block_found = True
                    break
            except:
                pass
        
        if not title_block_found:
            compliance_issues.append("Title block not found or incomplete")
            compliance_score -= 15
        
        # Check for dimension consistency
        dimensions = list(msp.query('DIMENSION'))
        if len(dimensions) == 0:
            compliance_issues.append("No dimensions found in drawing")
            compliance_score -= 10
        
        return {
            'compliance_score': max(0, compliance_score),
            'issues': compliance_issues,
            'recommendations': self._generate_compliance_recommendations(compliance_issues)
        }
    
    def _generate_compliance_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations based on compliance issues"""
        recommendations = []
        
        for issue in issues:
            if "layer" in issue.lower():
                recommendations.append("Review and standardize layer naming convention")
            elif "units" in issue.lower():
                recommendations.append("Define drawing units clearly in drawing setup")
            elif "title block" in issue.lower():
                recommendations.append("Add complete title block with project information")
            elif "dimension" in issue.lower():
                recommendations.append("Add dimensions for key measurements and verify accuracy")
        
        return recommendations
    
    def _extract_metadata(self, doc) -> Dict[str, Any]:
        """Extract drawing metadata and properties"""
        metadata = {}
        
        try:
            # Extract header variables
            header = doc.header
            metadata.update({
                'acadver': header.get('$ACADVER', 'Unknown'),
                'dwgcodepage': header.get('$DWGCODEPAGE', 'Unknown'),
                'insunits': header.get('$INSUNITS', 0),
                'measurement': header.get('$MEASUREMENT', 0),
                'lunits': header.get('$LUNITS', 2),
                'luprec': header.get('$LUPREC', 4)
            })
        except Exception as e:
            logger.warning(f"Error extracting header metadata: {str(e)}")
        
        # Extract custom properties if available
        try:
            if hasattr(doc, 'objects'):
                for obj in doc.objects:
                    if obj.dxftype() == 'DICTIONARY':
                        # Extract custom properties from dictionary objects
                        pass
        except Exception as e:
            logger.warning(f"Error extracting custom properties: {str(e)}")
        
        return metadata
    
    def _detect_drawing_units(self, doc) -> str:
        """Detect drawing units from header or content analysis"""
        try:
            header = doc.header
            insunits = header.get('$INSUNITS', 0)
            
            units_map = {
                0: 'unitless',
                1: 'inches',
                2: 'feet',
                3: 'miles',
                4: 'millimeters',
                5: 'centimeters',
                6: 'meters',
                7: 'kilometers'
            }
            
            return units_map.get(insunits, 'unknown')
        except:
            return 'unknown'
    
    def _get_drawing_limits(self, doc) -> Dict[str, float]:
        """Get drawing limits from header"""
        try:
            header = doc.header
            return {
                'limmin_x': header.get('$LIMMIN', (0, 0))[0],
                'limmin_y': header.get('$LIMMIN', (0, 0))[1],
                'limmax_x': header.get('$LIMMAX', (0, 0))[0],
                'limmax_y': header.get('$LIMMAX', (0, 0))[1]
            }
        except:
            return {'limmin_x': 0, 'limmin_y': 0, 'limmax_x': 0, 'limmax_y': 0}

# Global instance
cad_processor = CADProcessor()

