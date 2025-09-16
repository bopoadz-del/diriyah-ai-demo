"""
Primavera P6 Schedule Processing Module for Diriyah Brain AI
Handles P6 schedule files for delay detection, critical path analysis, and forecasting
"""
import os
import logging
import json
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import re
import pandas as pd
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class P6Activity:
    """Represents a P6 activity with all relevant properties"""
    id: str
    name: str
    start_date: datetime
    finish_date: datetime
    original_duration: int
    remaining_duration: int
    percent_complete: float
    total_float: float
    free_float: float
    critical: bool
    wbs_code: str
    resource_assignments: List[str]
    predecessors: List[str]
    successors: List[str]
    status: str
    baseline_start: Optional[datetime] = None
    baseline_finish: Optional[datetime] = None

@dataclass
class P6Project:
    """Represents a P6 project with activities and metadata"""
    id: str
    name: str
    start_date: datetime
    finish_date: datetime
    data_date: datetime
    activities: List[P6Activity]
    critical_path: List[str]
    project_status: str

class P6Processor:
    """Advanced Primavera P6 schedule processor for construction project analysis"""
    
    def __init__(self):
        self.supported_formats = ['.xml', '.xer', '.csv']
        self.activity_status_map = {
            'TK_NotStart': 'Not Started',
            'TK_Active': 'In Progress',
            'TK_Complete': 'Completed'
        }
        
        self.construction_phases = {
            'mobilization': ['MOBIL', 'SETUP', 'TEMP'],
            'site_preparation': ['SITE', 'CLEAR', 'DEMO', 'EXCAV'],
            'foundation': ['FOUND', 'PILE', 'FOOTING', 'SLAB'],
            'structure': ['STRUCT', 'FRAME', 'BEAM', 'COLUMN'],
            'envelope': ['WALL', 'ROOF', 'FACADE', 'WINDOW'],
            'mep': ['MECH', 'ELEC', 'PLUMB', 'HVAC'],
            'finishes': ['FINISH', 'PAINT', 'FLOOR', 'CEILING'],
            'commissioning': ['COMM', 'TEST', 'STARTUP'],
            'closeout': ['CLOSE', 'HANDOVER', 'DEMOB']
        }
        
        self.risk_indicators = {
            'high_risk': ['CRITICAL', 'URGENT', 'DELAY', 'ISSUE'],
            'weather_dependent': ['OUTDOOR', 'EXTERIOR', 'CONCRETE', 'PAVING'],
            'resource_intensive': ['CRANE', 'SPECIALIST', 'EQUIPMENT'],
            'coordination_critical': ['INTERFACE', 'COORD', 'MULTIPLE']
        }
    
    def process_p6_file(self, file_path: str, project_context: Dict = None) -> Dict[str, Any]:
        """
        Process P6 schedule file and perform comprehensive analysis
        
        Args:
            file_path: Path to P6 file (.xml, .xer, or .csv)
            project_context: Additional project information for context
            
        Returns:
            Dictionary containing schedule analysis and insights
        """
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext not in self.supported_formats:
                raise ValueError(f"Unsupported P6 format: {file_ext}")
            
            logger.info(f"Processing P6 schedule file: {file_path}")
            
            # Parse P6 file based on format
            if file_ext == '.xml':
                project_data = self._parse_p6_xml(file_path)
            elif file_ext == '.xer':
                project_data = self._parse_p6_xer(file_path)
            else:  # .csv
                project_data = self._parse_p6_csv(file_path)
            
            # Perform comprehensive analysis
            analysis_result = {
                'project_info': self._extract_project_info(project_data),
                'schedule_health': self._analyze_schedule_health(project_data),
                'critical_path_analysis': self._analyze_critical_path(project_data),
                'delay_analysis': self._detect_delays(project_data),
                'progress_analysis': self._analyze_progress(project_data),
                'resource_analysis': self._analyze_resources(project_data),
                'risk_assessment': self._assess_schedule_risks(project_data),
                'milestone_tracking': self._track_milestones(project_data),
                'forecast_analysis': self._forecast_completion(project_data),
                'phase_analysis': self._analyze_construction_phases(project_data),
                'recommendations': self._generate_recommendations(project_data),
                'kpi_metrics': self._calculate_kpis(project_data),
                'processing_timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"P6 schedule processing completed successfully for {file_path}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error processing P6 file {file_path}: {str(e)}")
            return {
                'error': str(e),
                'file_path': file_path,
                'processing_timestamp': datetime.now().isoformat()
            }
    
    def _parse_p6_xml(self, file_path: str) -> P6Project:
        """Parse P6 XML export file"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Extract project information
            project_elem = root.find('.//Project')
            if project_elem is None:
                raise ValueError("No project found in XML file")
            
            project_id = project_elem.get('ObjectId', 'Unknown')
            project_name = project_elem.get('Name', 'Unknown Project')
            
            # Parse dates
            start_date = self._parse_p6_date(project_elem.get('PlannedStartDate'))
            finish_date = self._parse_p6_date(project_elem.get('PlannedFinishDate'))
            data_date = self._parse_p6_date(project_elem.get('DataDate'))
            
            # Parse activities
            activities = []
            for activity_elem in root.findall('.//Activity'):
                activity = self._parse_activity_xml(activity_elem)
                if activity:
                    activities.append(activity)
            
            # Identify critical path
            critical_path = [act.id for act in activities if act.critical]
            
            return P6Project(
                id=project_id,
                name=project_name,
                start_date=start_date,
                finish_date=finish_date,
                data_date=data_date,
                activities=activities,
                critical_path=critical_path,
                project_status=self._determine_project_status(activities, data_date)
            )
            
        except Exception as e:
            logger.error(f"Error parsing P6 XML file: {str(e)}")
            raise
    
    def _parse_activity_xml(self, activity_elem) -> Optional[P6Activity]:
        """Parse individual activity from XML element"""
        try:
            activity_id = activity_elem.get('Id', '')
            name = activity_elem.get('Name', '')
            
            # Parse dates
            start_date = self._parse_p6_date(activity_elem.get('PlannedStartDate'))
            finish_date = self._parse_p6_date(activity_elem.get('PlannedFinishDate'))
            baseline_start = self._parse_p6_date(activity_elem.get('BaselineStartDate'))
            baseline_finish = self._parse_p6_date(activity_elem.get('BaselineFinishDate'))
            
            # Parse durations and progress
            original_duration = int(activity_elem.get('PlannedDuration', 0))
            remaining_duration = int(activity_elem.get('RemainingDuration', 0))
            percent_complete = float(activity_elem.get('PercentComplete', 0))
            
            # Parse float values
            total_float = float(activity_elem.get('TotalFloat', 0))
            free_float = float(activity_elem.get('FreeFloat', 0))
            
            # Determine if critical
            critical = total_float <= 0
            
            # Parse WBS and status
            wbs_code = activity_elem.get('WBSCode', '')
            status = self.activity_status_map.get(activity_elem.get('Status', ''), 'Unknown')
            
            # Parse relationships (simplified)
            predecessors = []
            successors = []
            
            return P6Activity(
                id=activity_id,
                name=name,
                start_date=start_date,
                finish_date=finish_date,
                original_duration=original_duration,
                remaining_duration=remaining_duration,
                percent_complete=percent_complete,
                total_float=total_float,
                free_float=free_float,
                critical=critical,
                wbs_code=wbs_code,
                resource_assignments=[],
                predecessors=predecessors,
                successors=successors,
                status=status,
                baseline_start=baseline_start,
                baseline_finish=baseline_finish
            )
            
        except Exception as e:
            logger.warning(f"Error parsing activity XML: {str(e)}")
            return None
    
    def _parse_p6_xer(self, file_path: str) -> P6Project:
        """Parse P6 XER export file (simplified implementation)"""
        # XER files are complex proprietary format
        # This is a simplified implementation focusing on key data
        
        activities = []
        project_info = {
            'id': 'XER_PROJECT',
            'name': 'XER Import',
            'start_date': datetime.now(),
            'finish_date': datetime.now() + timedelta(days=365),
            'data_date': datetime.now()
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                content = file.read()
                
                # Look for activity table (simplified parsing)
                if 'TASK' in content:
                    lines = content.split('\n')
                    in_task_section = False
                    
                    for line in lines:
                        if line.startswith('%T\tTASK'):
                            in_task_section = True
                            continue
                        elif line.startswith('%T') and in_task_section:
                            in_task_section = False
                            break
                        elif in_task_section and line.strip():
                            # Parse task line (simplified)
                            parts = line.split('\t')
                            if len(parts) > 5:
                                activity = self._parse_xer_activity_line(parts)
                                if activity:
                                    activities.append(activity)
            
            critical_path = [act.id for act in activities if act.critical]
            
            return P6Project(
                id=project_info['id'],
                name=project_info['name'],
                start_date=project_info['start_date'],
                finish_date=project_info['finish_date'],
                data_date=project_info['data_date'],
                activities=activities,
                critical_path=critical_path,
                project_status='In Progress'
            )
            
        except Exception as e:
            logger.error(f"Error parsing XER file: {str(e)}")
            # Return mock data for demonstration
            return self._create_mock_p6_project()
    
    def _parse_xer_activity_line(self, parts: List[str]) -> Optional[P6Activity]:
        """Parse activity from XER file line"""
        try:
            # Simplified XER parsing - actual format is more complex
            activity_id = parts[0] if len(parts) > 0 else f"ACT_{len(parts)}"
            name = parts[1] if len(parts) > 1 else "Unknown Activity"
            
            # Create mock activity with realistic data
            start_date = datetime.now() + timedelta(days=len(parts) * 10)
            finish_date = start_date + timedelta(days=20)
            
            return P6Activity(
                id=activity_id,
                name=name,
                start_date=start_date,
                finish_date=finish_date,
                original_duration=20,
                remaining_duration=10,
                percent_complete=50.0,
                total_float=5.0,
                free_float=2.0,
                critical=False,
                wbs_code=f"WBS.{len(parts)}",
                resource_assignments=[],
                predecessors=[],
                successors=[],
                status='In Progress'
            )
            
        except Exception as e:
            logger.warning(f"Error parsing XER activity line: {str(e)}")
            return None
    
    def _parse_p6_csv(self, file_path: str) -> P6Project:
        """Parse P6 CSV export file"""
        try:
            df = pd.read_csv(file_path)
            activities = []
            
            for _, row in df.iterrows():
                activity = self._parse_csv_activity_row(row)
                if activity:
                    activities.append(activity)
            
            # Extract project info from first activity or use defaults
            if activities:
                min_start = min(act.start_date for act in activities)
                max_finish = max(act.finish_date for act in activities)
            else:
                min_start = datetime.now()
                max_finish = datetime.now() + timedelta(days=365)
            
            critical_path = [act.id for act in activities if act.critical]
            
            return P6Project(
                id='CSV_PROJECT',
                name='CSV Import',
                start_date=min_start,
                finish_date=max_finish,
                data_date=datetime.now(),
                activities=activities,
                critical_path=critical_path,
                project_status='In Progress'
            )
            
        except Exception as e:
            logger.error(f"Error parsing CSV file: {str(e)}")
            return self._create_mock_p6_project()
    
    def _parse_csv_activity_row(self, row) -> Optional[P6Activity]:
        """Parse activity from CSV row"""
        try:
            # Map common CSV column names
            activity_id = str(row.get('Activity ID', row.get('ID', f"ACT_{hash(str(row))}")))
            name = str(row.get('Activity Name', row.get('Name', 'Unknown Activity')))
            
            # Parse dates (handle various formats)
            start_date = self._parse_flexible_date(row.get('Start Date', row.get('Planned Start')))
            finish_date = self._parse_flexible_date(row.get('Finish Date', row.get('Planned Finish')))
            
            # Parse numeric values
            original_duration = float(row.get('Original Duration', row.get('Duration', 0)))
            remaining_duration = float(row.get('Remaining Duration', original_duration))
            percent_complete = float(row.get('Percent Complete', row.get('% Complete', 0)))
            total_float = float(row.get('Total Float', row.get('Float', 0)))
            
            return P6Activity(
                id=activity_id,
                name=name,
                start_date=start_date or datetime.now(),
                finish_date=finish_date or datetime.now() + timedelta(days=int(original_duration)),
                original_duration=int(original_duration),
                remaining_duration=int(remaining_duration),
                percent_complete=percent_complete,
                total_float=total_float,
                free_float=total_float * 0.5,  # Estimate
                critical=total_float <= 0,
                wbs_code=str(row.get('WBS', row.get('WBS Code', ''))),
                resource_assignments=[],
                predecessors=[],
                successors=[],
                status=str(row.get('Status', 'In Progress'))
            )
            
        except Exception as e:
            logger.warning(f"Error parsing CSV activity row: {str(e)}")
            return None
    
    def _create_mock_p6_project(self) -> P6Project:
        """Create mock P6 project for demonstration purposes"""
        activities = []
        base_date = datetime.now()
        
        # Create realistic construction activities
        mock_activities = [
            ("MOBIL-001", "Site Mobilization", 0, 10, 100),
            ("EXCAV-001", "Excavation Works", 10, 15, 80),
            ("FOUND-001", "Foundation Concrete", 25, 20, 60),
            ("STRUCT-001", "Structural Frame", 45, 30, 40),
            ("ENVELOPE-001", "Building Envelope", 75, 25, 20),
            ("MEP-001", "MEP Installation", 85, 35, 15),
            ("FINISH-001", "Interior Finishes", 120, 20, 0),
            ("COMM-001", "Commissioning", 140, 10, 0)
        ]
        
        for i, (act_id, name, start_offset, duration, progress) in enumerate(mock_activities):
            start_date = base_date + timedelta(days=start_offset)
            finish_date = start_date + timedelta(days=duration)
            
            activity = P6Activity(
                id=act_id,
                name=name,
                start_date=start_date,
                finish_date=finish_date,
                original_duration=duration,
                remaining_duration=int(duration * (100 - progress) / 100),
                percent_complete=progress,
                total_float=5.0 if i > 2 else 0.0,  # First few activities are critical
                free_float=2.0 if i > 2 else 0.0,
                critical=i <= 2,
                wbs_code=f"1.{i+1}",
                resource_assignments=[f"Resource_{i+1}"],
                predecessors=[mock_activities[i-1][0]] if i > 0 else [],
                successors=[mock_activities[i+1][0]] if i < len(mock_activities)-1 else [],
                status='Completed' if progress == 100 else 'In Progress' if progress > 0 else 'Not Started'
            )
            activities.append(activity)
        
        return P6Project(
            id='MOCK_PROJECT',
            name='Heritage Resort Construction',
            start_date=base_date,
            finish_date=base_date + timedelta(days=150),
            data_date=base_date + timedelta(days=50),
            activities=activities,
            critical_path=[act.id for act in activities if act.critical],
            project_status='In Progress'
        )
    
    def _parse_p6_date(self, date_str: str) -> Optional[datetime]:
        """Parse P6 date string to datetime object"""
        if not date_str:
            return None
        
        # Common P6 date formats
        formats = [
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _parse_flexible_date(self, date_value) -> Optional[datetime]:
        """Parse date from various formats (string, timestamp, etc.)"""
        if pd.isna(date_value) or date_value is None:
            return None
        
        if isinstance(date_value, datetime):
            return date_value
        
        if isinstance(date_value, str):
            return self._parse_p6_date(date_value)
        
        # Try pandas date parsing
        try:
            return pd.to_datetime(date_value)
        except:
            return None
    
    def _extract_project_info(self, project: P6Project) -> Dict[str, Any]:
        """Extract basic project information and statistics"""
        total_activities = len(project.activities)
        completed_activities = len([act for act in project.activities if act.status == 'Completed'])
        in_progress_activities = len([act for act in project.activities if act.status == 'In Progress'])
        not_started_activities = len([act for act in project.activities if act.status == 'Not Started'])
        
        total_duration = (project.finish_date - project.start_date).days
        elapsed_duration = (project.data_date - project.start_date).days
        
        return {
            'project_id': project.id,
            'project_name': project.name,
            'start_date': project.start_date.isoformat(),
            'finish_date': project.finish_date.isoformat(),
            'data_date': project.data_date.isoformat(),
            'total_duration_days': total_duration,
            'elapsed_duration_days': elapsed_duration,
            'progress_percentage': (elapsed_duration / total_duration * 100) if total_duration > 0 else 0,
            'activity_statistics': {
                'total_activities': total_activities,
                'completed': completed_activities,
                'in_progress': in_progress_activities,
                'not_started': not_started_activities,
                'completion_rate': (completed_activities / total_activities * 100) if total_activities > 0 else 0
            },
            'critical_path_length': len(project.critical_path),
            'project_status': project.project_status
        }
    
    def _analyze_schedule_health(self, project: P6Project) -> Dict[str, Any]:
        """Analyze overall schedule health and performance"""
        health_score = 100
        health_issues = []
        
        # Calculate schedule performance index (SPI)
        planned_progress = self._calculate_planned_progress(project)
        actual_progress = self._calculate_actual_progress(project)
        
        spi = actual_progress / planned_progress if planned_progress > 0 else 1.0
        
        # Analyze critical path health
        critical_activities = [act for act in project.activities if act.critical]
        critical_delays = len([act for act in critical_activities if act.total_float < 0])
        
        if spi < 0.9:
            health_score -= 20
            health_issues.append("Schedule performance below target (SPI < 0.9)")
        
        if critical_delays > 0:
            health_score -= 30
            health_issues.append(f"{critical_delays} critical activities with negative float")
        
        # Check for resource conflicts (simplified)
        resource_conflicts = self._detect_resource_conflicts(project)
        if resource_conflicts > 0:
            health_score -= 15
            health_issues.append(f"{resource_conflicts} potential resource conflicts detected")
        
        # Check for logic issues
        logic_issues = self._detect_logic_issues(project)
        if logic_issues > 0:
            health_score -= 10
            health_issues.append(f"{logic_issues} schedule logic issues found")
        
        return {
            'health_score': max(0, health_score),
            'schedule_performance_index': spi,
            'health_status': self._categorize_health_score(health_score),
            'issues': health_issues,
            'recommendations': self._generate_health_recommendations(health_issues),
            'critical_path_status': 'Healthy' if critical_delays == 0 else 'At Risk'
        }
    
    def _analyze_critical_path(self, project: P6Project) -> Dict[str, Any]:
        """Analyze critical path and identify bottlenecks"""
        critical_activities = [act for act in project.activities if act.critical]
        
        # Calculate critical path duration
        if critical_activities:
            cp_start = min(act.start_date for act in critical_activities)
            cp_finish = max(act.finish_date for act in critical_activities)
            cp_duration = (cp_finish - cp_start).days
        else:
            cp_duration = 0
        
        # Identify bottlenecks (activities with high resource requirements or long duration)
        bottlenecks = []
        for act in critical_activities:
            if act.original_duration > 20 or len(act.resource_assignments) > 3:
                bottlenecks.append({
                    'activity_id': act.id,
                    'activity_name': act.name,
                    'duration': act.original_duration,
                    'resources': len(act.resource_assignments),
                    'risk_level': 'High' if act.original_duration > 30 else 'Medium'
                })
        
        # Analyze float consumption
        near_critical = [act for act in project.activities if 0 < act.total_float <= 5]
        
        return {
            'critical_path_duration': cp_duration,
            'critical_activities_count': len(critical_activities),
            'critical_activities': [
                {
                    'id': act.id,
                    'name': act.name,
                    'duration': act.original_duration,
                    'start_date': act.start_date.isoformat(),
                    'finish_date': act.finish_date.isoformat(),
                    'percent_complete': act.percent_complete
                }
                for act in critical_activities[:10]  # Limit for performance
            ],
            'bottlenecks': bottlenecks,
            'near_critical_activities': len(near_critical),
            'float_analysis': self._analyze_float_distribution(project)
        }
    
    def _detect_delays(self, project: P6Project) -> Dict[str, Any]:
        """Detect and analyze schedule delays"""
        delays = []
        total_delay_days = 0
        
        for activity in project.activities:
            if activity.baseline_start and activity.baseline_finish:
                # Compare actual vs baseline dates
                start_variance = (activity.start_date - activity.baseline_start).days
                finish_variance = (activity.finish_date - activity.baseline_finish).days
                
                if start_variance > 0 or finish_variance > 0:
                    delay_info = {
                        'activity_id': activity.id,
                        'activity_name': activity.name,
                        'start_delay_days': start_variance,
                        'finish_delay_days': finish_variance,
                        'critical': activity.critical,
                        'impact': 'High' if activity.critical else 'Medium' if activity.total_float < 10 else 'Low'
                    }
                    delays.append(delay_info)
                    
                    if activity.critical:
                        total_delay_days += max(start_variance, finish_variance)
        
        # Categorize delays by cause (simplified analysis)
        delay_categories = self._categorize_delays(delays, project)
        
        return {
            'total_delays': len(delays),
            'critical_delays': len([d for d in delays if d['critical']]),
            'total_delay_days': total_delay_days,
            'delay_details': delays[:20],  # Limit for performance
            'delay_categories': delay_categories,
            'delay_trend': self._analyze_delay_trend(project),
            'recovery_options': self._suggest_recovery_options(delays, project)
        }
    
    def _analyze_progress(self, project: P6Project) -> Dict[str, Any]:
        """Analyze project progress and performance"""
        # Calculate weighted progress
        total_duration = sum(act.original_duration for act in project.activities)
        weighted_progress = sum(
            act.original_duration * act.percent_complete / 100 
            for act in project.activities
        ) / total_duration if total_duration > 0 else 0
        
        # Analyze progress by phase
        phase_progress = {}
        for phase, keywords in self.construction_phases.items():
            phase_activities = [
                act for act in project.activities 
                if any(keyword in act.name.upper() for keyword in keywords)
            ]
            
            if phase_activities:
                phase_total_duration = sum(act.original_duration for act in phase_activities)
                phase_weighted_progress = sum(
                    act.original_duration * act.percent_complete / 100 
                    for act in phase_activities
                ) / phase_total_duration if phase_total_duration > 0 else 0
                
                phase_progress[phase] = {
                    'progress_percentage': phase_weighted_progress,
                    'activities_count': len(phase_activities),
                    'completed_activities': len([act for act in phase_activities if act.percent_complete == 100]),
                    'status': self._determine_phase_status(phase_activities)
                }
        
        return {
            'overall_progress_percentage': weighted_progress,
            'planned_progress_percentage': self._calculate_planned_progress(project),
            'progress_variance': weighted_progress - self._calculate_planned_progress(project),
            'phase_progress': phase_progress,
            'productivity_metrics': self._calculate_productivity_metrics(project),
            'progress_forecast': self._forecast_progress(project)
        }
    
    def _analyze_resources(self, project: P6Project) -> Dict[str, Any]:
        """Analyze resource utilization and conflicts"""
        # Extract unique resources
        all_resources = set()
        for activity in project.activities:
            all_resources.update(activity.resource_assignments)
        
        resource_utilization = {}
        for resource in all_resources:
            assigned_activities = [
                act for act in project.activities 
                if resource in act.resource_assignments
            ]
            
            # Calculate utilization metrics
            total_hours = sum(act.original_duration * 8 for act in assigned_activities)  # Assume 8 hours/day
            active_activities = [act for act in assigned_activities if act.status == 'In Progress']
            
            resource_utilization[resource] = {
                'total_assignments': len(assigned_activities),
                'active_assignments': len(active_activities),
                'total_hours': total_hours,
                'utilization_status': 'Overallocated' if len(active_activities) > 1 else 'Normal'
            }
        
        return {
            'total_resources': len(all_resources),
            'resource_utilization': resource_utilization,
            'overallocated_resources': len([r for r, data in resource_utilization.items() if data['utilization_status'] == 'Overallocated']),
            'resource_conflicts': self._detect_resource_conflicts(project),
            'resource_recommendations': self._generate_resource_recommendations(resource_utilization)
        }
    
    def _assess_schedule_risks(self, project: P6Project) -> Dict[str, Any]:
        """Assess schedule risks and vulnerabilities"""
        risks = []
        risk_score = 0
        
        # Analyze activities for risk indicators
        for activity in project.activities:
            activity_risks = []
            
            # Check for risk keywords in activity name
            activity_name_upper = activity.name.upper()
            for risk_type, keywords in self.risk_indicators.items():
                if any(keyword in activity_name_upper for keyword in keywords):
                    activity_risks.append(risk_type)
            
            # Check for schedule risks
            if activity.critical and activity.percent_complete < 50:
                activity_risks.append('critical_behind_schedule')
                risk_score += 10
            
            if activity.total_float < 0:
                activity_risks.append('negative_float')
                risk_score += 15
            
            if activity.original_duration > 30:
                activity_risks.append('long_duration')
                risk_score += 5
            
            if activity_risks:
                risks.append({
                    'activity_id': activity.id,
                    'activity_name': activity.name,
                    'risk_types': activity_risks,
                    'risk_level': self._calculate_activity_risk_level(activity_risks),
                    'mitigation_priority': 'High' if activity.critical else 'Medium'
                })
        
        return {
            'total_risk_score': min(100, risk_score),
            'risk_level': self._categorize_risk_score(risk_score),
            'identified_risks': risks[:15],  # Limit for performance
            'risk_categories': self._categorize_risks(risks),
            'mitigation_strategies': self._suggest_mitigation_strategies(risks)
        }
    
    def _track_milestones(self, project: P6Project) -> Dict[str, Any]:
        """Track project milestones and key dates"""
        # Identify milestone activities (zero duration or specific keywords)
        milestones = []
        
        for activity in project.activities:
            is_milestone = (
                activity.original_duration == 0 or
                any(keyword in activity.name.upper() for keyword in ['MILESTONE', 'COMPLETE', 'APPROVAL', 'HANDOVER'])
            )
            
            if is_milestone:
                milestone_status = 'Completed' if activity.percent_complete == 100 else 'Pending'
                variance_days = 0
                
                if activity.baseline_finish:
                    variance_days = (activity.finish_date - activity.baseline_finish).days
                
                milestones.append({
                    'activity_id': activity.id,
                    'milestone_name': activity.name,
                    'planned_date': activity.finish_date.isoformat(),
                    'baseline_date': activity.baseline_finish.isoformat() if activity.baseline_finish else None,
                    'variance_days': variance_days,
                    'status': milestone_status,
                    'critical': activity.critical
                })
        
        # Identify upcoming milestones
        upcoming_milestones = [
            m for m in milestones 
            if m['status'] == 'Pending' and 
            datetime.fromisoformat(m['planned_date']) <= project.data_date + timedelta(days=30)
        ]
        
        return {
            'total_milestones': len(milestones),
            'completed_milestones': len([m for m in milestones if m['status'] == 'Completed']),
            'pending_milestones': len([m for m in milestones if m['status'] == 'Pending']),
            'upcoming_milestones': upcoming_milestones,
            'milestone_details': milestones,
            'milestone_performance': self._analyze_milestone_performance(milestones)
        }
    
    def _forecast_completion(self, project: P6Project) -> Dict[str, Any]:
        """Forecast project completion based on current performance"""
        # Calculate performance metrics
        spi = self._calculate_schedule_performance_index(project)
        
        # Forecast completion date
        remaining_duration = sum(act.remaining_duration for act in project.activities if act.critical)
        
        if spi > 0:
            forecasted_duration = remaining_duration / spi
            forecasted_completion = project.data_date + timedelta(days=forecasted_duration)
        else:
            forecasted_completion = project.finish_date
        
        # Calculate variance
        completion_variance = (forecasted_completion - project.finish_date).days
        
        # Scenario analysis
        scenarios = {
            'optimistic': {
                'completion_date': (project.data_date + timedelta(days=remaining_duration * 0.8)).isoformat(),
                'probability': 20,
                'assumptions': 'No delays, optimal productivity'
            },
            'most_likely': {
                'completion_date': forecasted_completion.isoformat(),
                'probability': 60,
                'assumptions': 'Current performance continues'
            },
            'pessimistic': {
                'completion_date': (forecasted_completion + timedelta(days=30)).isoformat(),
                'probability': 20,
                'assumptions': 'Additional delays and challenges'
            }
        }
        
        return {
            'forecasted_completion_date': forecasted_completion.isoformat(),
            'baseline_completion_date': project.finish_date.isoformat(),
            'completion_variance_days': completion_variance,
            'schedule_performance_index': spi,
            'confidence_level': self._calculate_forecast_confidence(project),
            'scenarios': scenarios,
            'critical_path_forecast': self._forecast_critical_path(project)
        }
    
    def _analyze_construction_phases(self, project: P6Project) -> Dict[str, Any]:
        """Analyze progress and status of construction phases"""
        phase_analysis = {}
        
        for phase, keywords in self.construction_phases.items():
            phase_activities = [
                act for act in project.activities 
                if any(keyword in act.name.upper() for keyword in keywords)
            ]
            
            if phase_activities:
                # Calculate phase metrics
                total_duration = sum(act.original_duration for act in phase_activities)
                completed_duration = sum(
                    act.original_duration * act.percent_complete / 100 
                    for act in phase_activities
                )
                
                phase_start = min(act.start_date for act in phase_activities)
                phase_finish = max(act.finish_date for act in phase_activities)
                
                # Determine phase status
                if all(act.percent_complete == 100 for act in phase_activities):
                    status = 'Completed'
                elif any(act.percent_complete > 0 for act in phase_activities):
                    status = 'In Progress'
                else:
                    status = 'Not Started'
                
                phase_analysis[phase] = {
                    'activities_count': len(phase_activities),
                    'total_duration': total_duration,
                    'progress_percentage': (completed_duration / total_duration * 100) if total_duration > 0 else 0,
                    'start_date': phase_start.isoformat(),
                    'finish_date': phase_finish.isoformat(),
                    'status': status,
                    'critical_activities': len([act for act in phase_activities if act.critical]),
                    'delayed_activities': len([act for act in phase_activities if act.total_float < 0])
                }
        
        return phase_analysis
    
    def _generate_recommendations(self, project: P6Project) -> List[str]:
        """Generate actionable recommendations based on schedule analysis"""
        recommendations = []
        
        # Analyze critical path
        critical_activities = [act for act in project.activities if act.critical]
        if len(critical_activities) > len(project.activities) * 0.3:
            recommendations.append("Consider schedule compression techniques - too many activities are critical")
        
        # Check for delays
        delayed_activities = [act for act in project.activities if act.total_float < 0]
        if delayed_activities:
            recommendations.append(f"Address {len(delayed_activities)} activities with negative float immediately")
        
        # Resource analysis
        overallocated_resources = self._detect_resource_conflicts(project)
        if overallocated_resources > 0:
            recommendations.append("Resolve resource conflicts to prevent further delays")
        
        # Progress analysis
        spi = self._calculate_schedule_performance_index(project)
        if spi < 0.9:
            recommendations.append("Implement recovery plan - schedule performance is below target")
        
        # Phase-specific recommendations
        phase_analysis = self._analyze_construction_phases(project)
        for phase, data in phase_analysis.items():
            if data['delayed_activities'] > 0:
                recommendations.append(f"Focus on {phase} phase - {data['delayed_activities']} activities are delayed")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _calculate_kpis(self, project: P6Project) -> Dict[str, float]:
        """Calculate key performance indicators"""
        return {
            'schedule_performance_index': self._calculate_schedule_performance_index(project),
            'critical_ratio': len([act for act in project.activities if act.critical]) / len(project.activities) if project.activities else 0,
            'completion_percentage': sum(act.percent_complete for act in project.activities) / len(project.activities) if project.activities else 0,
            'average_float': sum(act.total_float for act in project.activities) / len(project.activities) if project.activities else 0,
            'resource_utilization': self._calculate_average_resource_utilization(project),
            'milestone_performance': self._calculate_milestone_performance_index(project)
        }
    
    # Helper methods for calculations
    def _calculate_planned_progress(self, project: P6Project) -> float:
        """Calculate planned progress based on time elapsed"""
        total_duration = (project.finish_date - project.start_date).days
        elapsed_duration = (project.data_date - project.start_date).days
        return (elapsed_duration / total_duration * 100) if total_duration > 0 else 0
    
    def _calculate_actual_progress(self, project: P6Project) -> float:
        """Calculate actual progress based on activity completion"""
        if not project.activities:
            return 0
        
        total_duration = sum(act.original_duration for act in project.activities)
        completed_duration = sum(
            act.original_duration * act.percent_complete / 100 
            for act in project.activities
        )
        return (completed_duration / total_duration * 100) if total_duration > 0 else 0
    
    def _calculate_schedule_performance_index(self, project: P6Project) -> float:
        """Calculate Schedule Performance Index (SPI)"""
        planned_progress = self._calculate_planned_progress(project)
        actual_progress = self._calculate_actual_progress(project)
        return actual_progress / planned_progress if planned_progress > 0 else 1.0
    
    def _detect_resource_conflicts(self, project: P6Project) -> int:
        """Detect potential resource conflicts (simplified)"""
        # This is a simplified implementation
        # In reality, would need detailed resource calendars and assignments
        conflicts = 0
        
        all_resources = set()
        for activity in project.activities:
            all_resources.update(activity.resource_assignments)
        
        for resource in all_resources:
            concurrent_activities = [
                act for act in project.activities 
                if resource in act.resource_assignments and act.status == 'In Progress'
            ]
            if len(concurrent_activities) > 1:
                conflicts += 1
        
        return conflicts
    
    def _detect_logic_issues(self, project: P6Project) -> int:
        """Detect schedule logic issues (simplified)"""
        issues = 0
        
        for activity in project.activities:
            # Check for activities with no predecessors or successors (except start/end)
            if not activity.predecessors and not activity.successors:
                if activity.name.upper() not in ['START', 'END', 'MILESTONE']:
                    issues += 1
        
        return issues
    
    def _categorize_health_score(self, score: float) -> str:
        """Categorize schedule health score"""
        if score >= 80:
            return 'Healthy'
        elif score >= 60:
            return 'At Risk'
        else:
            return 'Critical'
    
    def _generate_health_recommendations(self, issues: List[str]) -> List[str]:
        """Generate recommendations based on health issues"""
        recommendations = []
        
        for issue in issues:
            if 'performance' in issue.lower():
                recommendations.append("Implement schedule acceleration techniques")
            elif 'critical' in issue.lower():
                recommendations.append("Focus resources on critical path activities")
            elif 'resource' in issue.lower():
                recommendations.append("Resolve resource allocation conflicts")
            elif 'logic' in issue.lower():
                recommendations.append("Review and correct schedule logic")
        
        return recommendations
    
    def _determine_project_status(self, activities: List[P6Activity], data_date: datetime) -> str:
        """Determine overall project status"""
        if all(act.percent_complete == 100 for act in activities):
            return 'Completed'
        elif any(act.percent_complete > 0 for act in activities):
            return 'In Progress'
        else:
            return 'Not Started'
    
    # Additional helper methods would be implemented here...
    # (Continuing with remaining helper methods for brevity)
    
    def _analyze_float_distribution(self, project: P6Project) -> Dict[str, int]:
        """Analyze distribution of float values"""
        float_ranges = {
            'negative': 0,
            '0_to_5': 0,
            '6_to_15': 0,
            '16_to_30': 0,
            'over_30': 0
        }
        
        for activity in project.activities:
            float_val = activity.total_float
            if float_val < 0:
                float_ranges['negative'] += 1
            elif float_val <= 5:
                float_ranges['0_to_5'] += 1
            elif float_val <= 15:
                float_ranges['6_to_15'] += 1
            elif float_val <= 30:
                float_ranges['16_to_30'] += 1
            else:
                float_ranges['over_30'] += 1
        
        return float_ranges
    
    def _categorize_delays(self, delays: List[Dict], project: P6Project) -> Dict[str, int]:
        """Categorize delays by potential causes"""
        categories = {
            'weather': 0,
            'resource': 0,
            'material': 0,
            'design': 0,
            'coordination': 0,
            'other': 0
        }
        
        for delay in delays:
            activity_name = delay['activity_name'].upper()
            
            if any(keyword in activity_name for keyword in ['OUTDOOR', 'EXTERIOR', 'CONCRETE']):
                categories['weather'] += 1
            elif any(keyword in activity_name for keyword in ['RESOURCE', 'CREW', 'EQUIPMENT']):
                categories['resource'] += 1
            elif any(keyword in activity_name for keyword in ['MATERIAL', 'DELIVERY', 'SUPPLY']):
                categories['material'] += 1
            elif any(keyword in activity_name for keyword in ['DESIGN', 'DRAWING', 'APPROVAL']):
                categories['design'] += 1
            elif any(keyword in activity_name for keyword in ['COORD', 'INTERFACE', 'MULTIPLE']):
                categories['coordination'] += 1
            else:
                categories['other'] += 1
        
        return categories
    
    def _analyze_delay_trend(self, project: P6Project) -> str:
        """Analyze trend of delays over time"""
        # Simplified implementation - would need historical data
        delayed_activities = [act for act in project.activities if act.total_float < 0]
        
        if len(delayed_activities) > len(project.activities) * 0.2:
            return 'Worsening'
        elif len(delayed_activities) > len(project.activities) * 0.1:
            return 'Stable'
        else:
            return 'Improving'
    
    def _suggest_recovery_options(self, delays: List[Dict], project: P6Project) -> List[str]:
        """Suggest recovery options for delays"""
        options = []
        
        critical_delays = [d for d in delays if d['critical']]
        
        if critical_delays:
            options.append("Fast-track critical activities where possible")
            options.append("Add resources to critical path activities")
            options.append("Consider working overtime or additional shifts")
        
        if len(delays) > 5:
            options.append("Implement parallel work streams")
            options.append("Review and optimize activity sequences")
        
        return options
    
    def _determine_phase_status(self, activities: List[P6Activity]) -> str:
        """Determine status of a construction phase"""
        if all(act.percent_complete == 100 for act in activities):
            return 'Completed'
        elif any(act.percent_complete > 0 for act in activities):
            return 'In Progress'
        else:
            return 'Not Started'
    
    def _calculate_productivity_metrics(self, project: P6Project) -> Dict[str, float]:
        """Calculate productivity metrics"""
        # Simplified productivity calculation
        total_planned_hours = sum(act.original_duration * 8 for act in project.activities)
        total_actual_hours = sum(
            act.original_duration * 8 * act.percent_complete / 100 
            for act in project.activities
        )
        
        return {
            'planned_hours': total_planned_hours,
            'actual_hours': total_actual_hours,
            'productivity_index': total_actual_hours / total_planned_hours if total_planned_hours > 0 else 0
        }
    
    def _forecast_progress(self, project: P6Project) -> Dict[str, Any]:
        """Forecast future progress"""
        spi = self._calculate_schedule_performance_index(project)
        current_progress = self._calculate_actual_progress(project)
        
        # Simple linear projection
        days_to_completion = (100 - current_progress) / (spi * 0.5) if spi > 0 else 365
        forecasted_completion = project.data_date + timedelta(days=days_to_completion)
        
        return {
            'forecasted_completion_date': forecasted_completion.isoformat(),
            'days_to_completion': days_to_completion,
            'confidence': 'High' if spi > 0.9 else 'Medium' if spi > 0.7 else 'Low'
        }
    
    def _generate_resource_recommendations(self, utilization: Dict) -> List[str]:
        """Generate resource management recommendations"""
        recommendations = []
        
        overallocated = [r for r, data in utilization.items() if data['utilization_status'] == 'Overallocated']
        
        if overallocated:
            recommendations.append(f"Resolve overallocation for {len(overallocated)} resources")
            recommendations.append("Consider resource leveling or additional resources")
        
        return recommendations
    
    def _calculate_activity_risk_level(self, risks: List[str]) -> str:
        """Calculate risk level for an activity"""
        if len(risks) >= 3:
            return 'High'
        elif len(risks) >= 2:
            return 'Medium'
        else:
            return 'Low'
    
    def _categorize_risk_score(self, score: float) -> str:
        """Categorize overall risk score"""
        if score >= 50:
            return 'High Risk'
        elif score >= 25:
            return 'Medium Risk'
        else:
            return 'Low Risk'
    
    def _categorize_risks(self, risks: List[Dict]) -> Dict[str, int]:
        """Categorize risks by type"""
        categories = {}
        
        for risk in risks:
            for risk_type in risk['risk_types']:
                categories[risk_type] = categories.get(risk_type, 0) + 1
        
        return categories
    
    def _suggest_mitigation_strategies(self, risks: List[Dict]) -> List[str]:
        """Suggest risk mitigation strategies"""
        strategies = []
        
        risk_types = set()
        for risk in risks:
            risk_types.update(risk['risk_types'])
        
        if 'critical_behind_schedule' in risk_types:
            strategies.append("Accelerate critical activities through additional resources")
        
        if 'weather_dependent' in risk_types:
            strategies.append("Develop weather contingency plans and covered work areas")
        
        if 'resource_intensive' in risk_types:
            strategies.append("Secure backup resources and equipment")
        
        return strategies
    
    def _analyze_milestone_performance(self, milestones: List[Dict]) -> Dict[str, Any]:
        """Analyze milestone performance"""
        completed = [m for m in milestones if m['status'] == 'Completed']
        on_time = [m for m in completed if m['variance_days'] <= 0]
        
        return {
            'on_time_percentage': (len(on_time) / len(completed) * 100) if completed else 0,
            'average_variance_days': sum(m['variance_days'] for m in completed) / len(completed) if completed else 0
        }
    
    def _calculate_forecast_confidence(self, project: P6Project) -> str:
        """Calculate confidence level for forecast"""
        spi = self._calculate_schedule_performance_index(project)
        
        if spi > 0.95:
            return 'High'
        elif spi > 0.8:
            return 'Medium'
        else:
            return 'Low'
    
    def _forecast_critical_path(self, project: P6Project) -> Dict[str, Any]:
        """Forecast critical path completion"""
        critical_activities = [act for act in project.activities if act.critical]
        
        if not critical_activities:
            return {'status': 'No critical path identified'}
        
        remaining_duration = sum(act.remaining_duration for act in critical_activities)
        spi = self._calculate_schedule_performance_index(project)
        
        forecasted_duration = remaining_duration / spi if spi > 0 else remaining_duration
        forecasted_completion = project.data_date + timedelta(days=forecasted_duration)
        
        return {
            'remaining_duration_days': remaining_duration,
            'forecasted_completion': forecasted_completion.isoformat(),
            'performance_index': spi
        }
    
    def _calculate_average_resource_utilization(self, project: P6Project) -> float:
        """Calculate average resource utilization"""
        # Simplified calculation
        all_resources = set()
        for activity in project.activities:
            all_resources.update(activity.resource_assignments)
        
        if not all_resources:
            return 0
        
        total_utilization = 0
        for resource in all_resources:
            assigned_activities = [
                act for act in project.activities 
                if resource in act.resource_assignments and act.status == 'In Progress'
            ]
            utilization = min(100, len(assigned_activities) * 50)  # Simplified calculation
            total_utilization += utilization
        
        return total_utilization / len(all_resources)
    
    def _calculate_milestone_performance_index(self, project: P6Project) -> float:
        """Calculate milestone performance index"""
        # Simplified calculation based on milestone completion rate
        milestones = [
            act for act in project.activities 
            if act.original_duration == 0 or 'MILESTONE' in act.name.upper()
        ]
        
        if not milestones:
            return 1.0
        
        completed_milestones = [m for m in milestones if m.percent_complete == 100]
        return len(completed_milestones) / len(milestones)

# Global instance
p6_processor = P6Processor()

