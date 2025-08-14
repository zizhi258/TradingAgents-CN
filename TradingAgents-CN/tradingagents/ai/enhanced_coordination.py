"""
Enhanced Multi-Agent Coordination System for TradingAgents-CN

This module provides advanced multi-agent coordination with LLM-powered agent selection,
consensus building, dynamic role assignment, and intelligent conflict resolution.
"""

import asyncio
import json
import numpy as np
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import networkx as nx
from collections import defaultdict, deque
import statistics
import math

# TradingAgents imports
from tradingagents.core.multi_model_manager import MultiModelManager, TaskResult, CollaborationResult
from tradingagents.utils.logging_init import get_logger

logger = get_logger("enhanced_coordination")


class AgentRole(Enum):
    """Enhanced agent role definitions"""
    # Core Financial Analysis Roles
    FUNDAMENTAL_EXPERT = "fundamental_expert"
    TECHNICAL_ANALYST = "technical_analyst" 
    NEWS_HUNTER = "news_hunter"
    SENTIMENT_ANALYST = "sentiment_analyst"
    RISK_MANAGER = "risk_manager"
    
    # Strategic Roles
    CHIEF_DECISION_OFFICER = "chief_decision_officer"
    POLICY_RESEARCHER = "policy_researcher"
    COMPLIANCE_OFFICER = "compliance_officer"
    
    # Specialized Roles
    TOOL_ENGINEER = "tool_engineer"
    CHARTING_ARTIST = "charting_artist"
    MARKET_MAKER = "market_maker"
    QUANTITATIVE_ANALYST = "quantitative_analyst"
    
    # Meta Roles (for coordination)
    COORDINATOR = "coordinator"
    MEDIATOR = "mediator"
    VALIDATOR = "validator"


class CoordinationMode(Enum):
    """Coordination modes for multi-agent workflows"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    DEMOCRATIC = "democratic"
    EXPERT_PANEL = "expert_panel"
    ADVERSARIAL = "adversarial"
    CONSENSUS_BUILDING = "consensus_building"


class ConsensusMethod(Enum):
    """Methods for building consensus"""
    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_AVERAGE = "weighted_average"
    DELPHI_METHOD = "delphi_method"
    BAYESIAN_FUSION = "bayesian_fusion"
    EXPERT_OVERRULE = "expert_overrule"


class ConflictResolutionStrategy(Enum):
    """Strategies for resolving agent conflicts"""
    DEBATE = "debate"
    EVIDENCE_BASED = "evidence_based"
    AUTHORITY_BASED = "authority_based"
    COMPROMISE = "compromise"
    ADDITIONAL_EXPERT = "additional_expert"


@dataclass
class AgentCapability:
    """Agent capability definition"""
    capability_name: str
    proficiency_level: float  # 0.0 to 1.0
    confidence: float = 0.8
    applicable_contexts: List[str] = field(default_factory=list)
    
    
@dataclass
class AgentProfile:
    """Enhanced agent profile with capabilities and preferences"""
    role: AgentRole
    name: str
    description: str
    capabilities: List[AgentCapability] = field(default_factory=list)
    expertise_domains: List[str] = field(default_factory=list)
    collaboration_preferences: Dict[str, float] = field(default_factory=dict)
    performance_history: Dict[str, float] = field(default_factory=dict)
    authority_level: float = 0.5  # 0.0 to 1.0
    reputation_score: float = 0.5  # Dynamic reputation
    last_active: Optional[datetime] = None


@dataclass
class CoordinationTask:
    """Task for multi-agent coordination"""
    task_id: str
    task_type: str
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    required_capabilities: List[str] = field(default_factory=list)
    complexity_level: str = "medium"
    deadline: Optional[datetime] = None
    priority: float = 0.5
    

@dataclass
class AgentOpinion:
    """Agent's opinion with confidence and reasoning"""
    agent_role: AgentRole
    position: str
    confidence: float
    reasoning: str
    evidence: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    

@dataclass
class ConsensusResult:
    """Result of consensus building process"""
    final_decision: str
    consensus_score: float  # 0.0 to 1.0
    participating_agents: List[AgentRole]
    method_used: ConsensusMethod
    individual_opinions: List[AgentOpinion]
    reasoning: str
    confidence: float
    dissenting_opinions: List[AgentOpinion] = field(default_factory=list)


class AgentPerformanceTracker:
    """Track and evaluate agent performance"""
    
    def __init__(self):
        self.performance_metrics = defaultdict(lambda: {
            'accuracy': deque(maxlen=100),
            'response_time': deque(maxlen=100),
            'collaboration_score': deque(maxlen=100),
            'confidence_calibration': deque(maxlen=100)
        })
        
    def record_performance(self, agent_role: AgentRole, 
                          accuracy: float, response_time: float,
                          collaboration_score: float, confidence_calibration: float):
        """Record performance metrics for an agent"""
        metrics = self.performance_metrics[agent_role]
        metrics['accuracy'].append(accuracy)
        metrics['response_time'].append(response_time)
        metrics['collaboration_score'].append(collaboration_score)
        metrics['confidence_calibration'].append(confidence_calibration)
    
    def get_agent_score(self, agent_role: AgentRole) -> Dict[str, float]:
        """Get comprehensive performance score for an agent"""
        metrics = self.performance_metrics[agent_role]
        
        if not metrics['accuracy']:
            return {'overall_score': 0.5, 'accuracy': 0.5, 'speed': 0.5, 'collaboration': 0.5}
        
        accuracy = statistics.mean(metrics['accuracy'])
        speed = 1.0 - (statistics.mean(metrics['response_time']) / 60.0)  # Normalize to 60s max
        collaboration = statistics.mean(metrics['collaboration_score'])
        calibration = statistics.mean(metrics['confidence_calibration'])
        
        # Weighted overall score
        overall_score = (
            accuracy * 0.4 + 
            speed * 0.2 + 
            collaboration * 0.3 + 
            calibration * 0.1
        )
        
        return {
            'overall_score': overall_score,
            'accuracy': accuracy,
            'speed': max(0.0, speed),
            'collaboration': collaboration,
            'calibration': calibration
        }


class DynamicAgentSelector:
    """Intelligently select agents for tasks based on capabilities and performance"""
    
    def __init__(self, llm_orchestrator=None):
        self.llm_orchestrator = llm_orchestrator
        self.agent_profiles: Dict[AgentRole, AgentProfile] = {}
        self.performance_tracker = AgentPerformanceTracker()
        self.collaboration_graph = nx.Graph()
        
        # Initialize default agent profiles
        self._initialize_default_profiles()
    
    def _initialize_default_profiles(self):
        """Initialize default agent profiles"""
        default_profiles = {
            AgentRole.FUNDAMENTAL_EXPERT: AgentProfile(
                role=AgentRole.FUNDAMENTAL_EXPERT,
                name="Fundamental Analysis Expert",
                description="Expert in company fundamentals, financial statements, and valuation",
                capabilities=[
                    AgentCapability("financial_analysis", 0.95),
                    AgentCapability("valuation_modeling", 0.9),
                    AgentCapability("earnings_analysis", 0.92)
                ],
                expertise_domains=["fundamentals", "valuation", "earnings", "financial_health"],
                authority_level=0.8
            ),
            
            AgentRole.TECHNICAL_ANALYST: AgentProfile(
                role=AgentRole.TECHNICAL_ANALYST,
                name="Technical Analysis Specialist",
                description="Expert in chart patterns, technical indicators, and price action",
                capabilities=[
                    AgentCapability("chart_analysis", 0.93),
                    AgentCapability("pattern_recognition", 0.9),
                    AgentCapability("indicator_analysis", 0.88)
                ],
                expertise_domains=["technical_analysis", "charts", "patterns", "indicators"],
                authority_level=0.75
            ),
            
            AgentRole.RISK_MANAGER: AgentProfile(
                role=AgentRole.RISK_MANAGER,
                name="Risk Assessment Manager",
                description="Specialist in risk analysis, portfolio management, and downside protection",
                capabilities=[
                    AgentCapability("risk_assessment", 0.95),
                    AgentCapability("portfolio_analysis", 0.9),
                    AgentCapability("stress_testing", 0.85)
                ],
                expertise_domains=["risk", "portfolio", "volatility", "correlation"],
                authority_level=0.9
            ),
            
            AgentRole.NEWS_HUNTER: AgentProfile(
                role=AgentRole.NEWS_HUNTER,
                name="News and Events Analyst",
                description="Expert in news analysis, market events, and information synthesis",
                capabilities=[
                    AgentCapability("news_analysis", 0.88),
                    AgentCapability("event_impact", 0.85),
                    AgentCapability("information_synthesis", 0.9)
                ],
                expertise_domains=["news", "events", "market_sentiment", "catalysts"],
                authority_level=0.7
            ),
            
            AgentRole.CHIEF_DECISION_OFFICER: AgentProfile(
                role=AgentRole.CHIEF_DECISION_OFFICER,
                name="Chief Decision Officer",
                description="Senior executive for final decision making and strategic oversight",
                capabilities=[
                    AgentCapability("strategic_thinking", 0.95),
                    AgentCapability("decision_making", 0.93),
                    AgentCapability("synthesis", 0.9)
                ],
                expertise_domains=["strategy", "decisions", "synthesis", "leadership"],
                authority_level=1.0
            )
        }
        
        for role, profile in default_profiles.items():
            self.agent_profiles[role] = profile
            self.collaboration_graph.add_node(role)
    
    async def select_agents_for_task(self, task: CoordinationTask,
                                   max_agents: int = 5) -> List[AgentRole]:
        """
        Intelligently select the best agents for a task
        
        Args:
            task: The coordination task
            max_agents: Maximum number of agents to select
            
        Returns:
            List of selected agent roles
        """
        try:
            # Get agent scores for all agents
            agent_scores = {}
            for role, profile in self.agent_profiles.items():
                score = self._calculate_task_fitness(profile, task)
                agent_scores[role] = score
            
            # Use AI for intelligent selection if available
            if self.llm_orchestrator:
                selected_agents = await self._ai_agent_selection(task, agent_scores, max_agents)
            else:
                selected_agents = self._heuristic_agent_selection(task, agent_scores, max_agents)
            
            logger.info(f"Selected {len(selected_agents)} agents for task: {task.task_type}")
            return selected_agents
            
        except Exception as e:
            logger.error(f"Agent selection failed: {e}")
            # Fallback to basic selection
            return list(self.agent_profiles.keys())[:max_agents]
    
    def _calculate_task_fitness(self, profile: AgentProfile, task: CoordinationTask) -> float:
        """Calculate how well an agent fits a task"""
        fitness_score = 0.0
        
        # Capability matching
        capability_score = 0.0
        if task.required_capabilities:
            matching_capabilities = [
                cap for cap in profile.capabilities 
                if cap.capability_name in task.required_capabilities
            ]
            if matching_capabilities:
                capability_score = sum(cap.proficiency_level for cap in matching_capabilities) / len(matching_capabilities)
        else:
            # Use average capability if no specific requirements
            capability_score = sum(cap.proficiency_level for cap in profile.capabilities) / max(len(profile.capabilities), 1)
        
        # Domain expertise matching
        domain_score = 0.0
        task_domains = task.context.get('domains', [])
        if task_domains:
            matching_domains = len(set(profile.expertise_domains) & set(task_domains))
            domain_score = matching_domains / len(task_domains)
        else:
            domain_score = 0.5  # Neutral if no specific domains
        
        # Performance history
        performance_metrics = self.performance_tracker.get_agent_score(profile.role)
        performance_score = performance_metrics['overall_score']
        
        # Authority level for high-priority tasks
        authority_score = profile.authority_level if task.priority > 0.7 else 0.5
        
        # Combine scores with weights
        fitness_score = (
            capability_score * 0.4 +
            domain_score * 0.25 +
            performance_score * 0.25 +
            authority_score * 0.1
        )
        
        return min(1.0, max(0.0, fitness_score))
    
    async def _ai_agent_selection(self, task: CoordinationTask,
                                agent_scores: Dict[AgentRole, float],
                                max_agents: int) -> List[AgentRole]:
        """Use AI to select agents intelligently"""
        
        # Create selection prompt
        agent_info = []
        for role, score in agent_scores.items():
            profile = self.agent_profiles[role]
            agent_info.append(f"- {role.value}: {profile.name} (fitness: {score:.2f}, authority: {profile.authority_level:.2f})")
        
        selection_prompt = f"""
Task: {task.description}
Task Type: {task.task_type}
Required Capabilities: {', '.join(task.required_capabilities) if task.required_capabilities else 'None specified'}
Priority: {task.priority}
Complexity: {task.complexity_level}
Max Agents: {max_agents}

Available Agents:
{chr(10).join(agent_info)}

Please select the {max_agents} most suitable agents for this task. Consider:
1. Capability alignment with task requirements
2. Complementary expertise for comprehensive analysis
3. Authority level for decision-making tasks
4. Collaboration effectiveness

Respond with a JSON list of agent role names (e.g., ["fundamental_expert", "risk_manager", "technical_analyst"])
"""
        
        try:
            result = await self.llm_orchestrator.execute_task(
                agent_role="coordinator",
                task_prompt=selection_prompt,
                task_type="agent_selection",
                context={'task_info': task.__dict__}
            )
            
            if result.success:
                # Parse AI response
                response = result.result.strip()
                if response.startswith('[') and response.endswith(']'):
                    selected_names = json.loads(response)
                    selected_roles = []
                    
                    for name in selected_names:
                        for role in AgentRole:
                            if role.value == name:
                                selected_roles.append(role)
                                break
                    
                    if selected_roles:
                        return selected_roles[:max_agents]
            
        except Exception as e:
            logger.warning(f"AI agent selection failed, using heuristic: {e}")
        
        # Fallback to heuristic selection
        return self._heuristic_agent_selection(task, agent_scores, max_agents)
    
    def _heuristic_agent_selection(self, task: CoordinationTask,
                                 agent_scores: Dict[AgentRole, float],
                                 max_agents: int) -> List[AgentRole]:
        """Heuristic agent selection based on scores and rules"""
        
        # Sort agents by fitness score
        sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)
        
        selected = []
        
        # Always include high-authority agents for important tasks
        if task.priority > 0.8:
            for role, score in sorted_agents:
                if self.agent_profiles[role].authority_level > 0.8 and len(selected) < max_agents:
                    selected.append(role)
        
        # Add complementary agents
        for role, score in sorted_agents:
            if role not in selected and len(selected) < max_agents:
                # Check for domain complementarity
                if self._is_complementary(role, selected, task):
                    selected.append(role)
        
        # Fill remaining slots with highest-scoring agents
        for role, score in sorted_agents:
            if role not in selected and len(selected) < max_agents:
                selected.append(role)
        
        return selected
    
    def _is_complementary(self, candidate_role: AgentRole, 
                         selected_roles: List[AgentRole],
                         task: CoordinationTask) -> bool:
        """Check if an agent provides complementary expertise"""
        if not selected_roles:
            return True
        
        candidate_domains = set(self.agent_profiles[candidate_role].expertise_domains)
        
        # Get combined domains of selected agents
        selected_domains = set()
        for role in selected_roles:
            selected_domains.update(self.agent_profiles[role].expertise_domains)
        
        # Check for new domains
        new_domains = candidate_domains - selected_domains
        
        # Agent is complementary if it adds new domains or has high authority
        return (len(new_domains) > 0 or 
                self.agent_profiles[candidate_role].authority_level > 0.8)


class ConsensusEngine:
    """Engine for building consensus among multiple agents"""
    
    def __init__(self, llm_orchestrator=None):
        self.llm_orchestrator = llm_orchestrator
        
    async def build_consensus(self, opinions: List[AgentOpinion],
                            method: ConsensusMethod = ConsensusMethod.WEIGHTED_AVERAGE,
                            context: Dict[str, Any] = None) -> ConsensusResult:
        """
        Build consensus from multiple agent opinions
        
        Args:
            opinions: List of agent opinions
            method: Consensus building method
            context: Additional context for consensus building
            
        Returns:
            ConsensusResult with final decision and metadata
        """
        try:
            context = context or {}
            
            if method == ConsensusMethod.MAJORITY_VOTE:
                return self._majority_vote_consensus(opinions)
            
            elif method == ConsensusMethod.WEIGHTED_AVERAGE:
                return await self._weighted_average_consensus(opinions, context)
            
            elif method == ConsensusMethod.DELPHI_METHOD:
                return await self._delphi_consensus(opinions, context)
            
            elif method == ConsensusMethod.BAYESIAN_FUSION:
                return self._bayesian_fusion_consensus(opinions)
            
            elif method == ConsensusMethod.EXPERT_OVERRULE:
                return self._expert_overrule_consensus(opinions)
            
            else:
                # Default to weighted average
                return await self._weighted_average_consensus(opinions, context)
                
        except Exception as e:
            logger.error(f"Consensus building failed: {e}")
            return ConsensusResult(
                final_decision="Consensus building failed due to technical error",
                consensus_score=0.0,
                participating_agents=[op.agent_role for op in opinions],
                method_used=method,
                individual_opinions=opinions,
                reasoning=f"Error: {str(e)}",
                confidence=0.0
            )
    
    def _majority_vote_consensus(self, opinions: List[AgentOpinion]) -> ConsensusResult:
        """Simple majority vote consensus"""
        
        # Group opinions by position
        position_votes = defaultdict(list)
        for opinion in opinions:
            position_votes[opinion.position].append(opinion)
        
        # Find majority position
        majority_position = max(position_votes.keys(), key=lambda k: len(position_votes[k]))
        majority_opinions = position_votes[majority_position]
        
        # Calculate consensus score
        consensus_score = len(majority_opinions) / len(opinions)
        
        # Get dissenting opinions
        dissenting_opinions = [op for op in opinions if op.position != majority_position]
        
        return ConsensusResult(
            final_decision=majority_position,
            consensus_score=consensus_score,
            participating_agents=[op.agent_role for op in opinions],
            method_used=ConsensusMethod.MAJORITY_VOTE,
            individual_opinions=opinions,
            reasoning=f"Majority vote: {len(majority_opinions)}/{len(opinions)} agents agreed",
            confidence=statistics.mean([op.confidence for op in majority_opinions]),
            dissenting_opinions=dissenting_opinions
        )
    
    async def _weighted_average_consensus(self, opinions: List[AgentOpinion],
                                        context: Dict[str, Any]) -> ConsensusResult:
        """Weighted average consensus based on agent authority and confidence"""
        
        if not opinions:
            return ConsensusResult(
                final_decision="No opinions provided",
                consensus_score=0.0,
                participating_agents=[],
                method_used=ConsensusMethod.WEIGHTED_AVERAGE,
                individual_opinions=[],
                reasoning="No opinions to process",
                confidence=0.0
            )
        
        # Calculate weights based on authority and confidence
        weights = []
        for opinion in opinions:
            # Base weight on confidence
            weight = opinion.confidence
            
            # Adjust for agent authority (if available)
            agent_authority = context.get('agent_authorities', {}).get(opinion.agent_role, 0.5)
            weight *= (1 + agent_authority)  # Boost by authority
            
            weights.append(weight)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight > 0:
            weights = [w / total_weight for w in weights]
        else:
            weights = [1.0 / len(opinions)] * len(opinions)
        
        # Use AI to synthesize weighted consensus if available
        if self.llm_orchestrator:
            final_decision = await self._ai_synthesis(opinions, weights, context)
        else:
            final_decision = self._simple_synthesis(opinions, weights)
        
        # Calculate consensus metrics
        consensus_score = self._calculate_consensus_score(opinions, weights)
        confidence = sum(op.confidence * w for op, w in zip(opinions, weights))
        
        return ConsensusResult(
            final_decision=final_decision,
            consensus_score=consensus_score,
            participating_agents=[op.agent_role for op in opinions],
            method_used=ConsensusMethod.WEIGHTED_AVERAGE,
            individual_opinions=opinions,
            reasoning="Weighted synthesis based on agent authority and confidence",
            confidence=confidence
        )
    
    async def _ai_synthesis(self, opinions: List[AgentOpinion], 
                          weights: List[float], context: Dict[str, Any]) -> str:
        """Use AI to synthesize consensus from weighted opinions"""
        
        # Prepare synthesis prompt
        weighted_opinions = []
        for opinion, weight in zip(opinions, weights):
            weighted_opinions.append(f"""
Agent: {opinion.agent_role.value} (Weight: {weight:.2f}, Confidence: {opinion.confidence:.2f})
Position: {opinion.position}
Reasoning: {opinion.reasoning}
Evidence: {', '.join(opinion.evidence) if opinion.evidence else 'None provided'}
""")
        
        synthesis_prompt = f"""
Please synthesize a consensus decision from the following weighted expert opinions:

{chr(10).join(weighted_opinions)}

Context: {json.dumps(context, indent=2)}

Create a balanced consensus that:
1. Incorporates insights from all agents proportional to their weights
2. Addresses key points of agreement and disagreement
3. Provides actionable recommendations
4. Acknowledges uncertainty where opinions diverge

Provide a comprehensive consensus decision that represents the collective wisdom of the expert panel.
"""
        
        try:
            result = await self.llm_orchestrator.execute_task(
                agent_role="mediator",
                task_prompt=synthesis_prompt,
                task_type="consensus_building",
                context=context
            )
            
            if result.success:
                return result.result
            else:
                return self._simple_synthesis(opinions, weights)
                
        except Exception as e:
            logger.warning(f"AI synthesis failed, using simple method: {e}")
            return self._simple_synthesis(opinions, weights)
    
    def _simple_synthesis(self, opinions: List[AgentOpinion], 
                         weights: List[float]) -> str:
        """Simple synthesis without AI"""
        
        # Find most common themes
        all_positions = [op.position for op in opinions]
        
        # Create basic synthesis
        synthesis = f"""
Consensus Analysis:

Key Positions:
{chr(10).join([f"- {op.agent_role.value}: {op.position}" for op in opinions])}

Synthesis: Based on the weighted analysis of {len(opinions)} expert opinions, 
the consensus suggests a balanced approach incorporating insights from all perspectives.

Confidence Level: {statistics.mean([op.confidence for op in opinions]):.2f}
"""
        return synthesis
    
    def _calculate_consensus_score(self, opinions: List[AgentOpinion], 
                                 weights: List[float]) -> float:
        """Calculate consensus score based on opinion similarity"""
        
        if len(opinions) <= 1:
            return 1.0
        
        # Simple similarity based on confidence alignment
        confidences = [op.confidence for op in opinions]
        confidence_var = statistics.variance(confidences) if len(confidences) > 1 else 0
        
        # High variance = low consensus
        consensus_score = max(0.0, 1.0 - confidence_var)
        
        return consensus_score
    
    async def _delphi_consensus(self, opinions: List[AgentOpinion],
                              context: Dict[str, Any]) -> ConsensusResult:
        """Modified Delphi method for consensus building"""
        
        # For now, implement a simplified version
        # In a full implementation, this would involve multiple rounds
        
        return await self._weighted_average_consensus(opinions, context)
    
    def _bayesian_fusion_consensus(self, opinions: List[AgentOpinion]) -> ConsensusResult:
        """Bayesian information fusion for consensus"""
        
        # Simplified Bayesian approach based on confidence levels
        # In practice, this would use proper Bayesian updating
        
        total_evidence = sum(op.confidence for op in opinions)
        
        # Weight opinions by normalized confidence
        weights = [op.confidence / total_evidence for op in opinions] if total_evidence > 0 else [1/len(opinions)] * len(opinions)
        
        # Create consensus decision
        final_decision = "Bayesian fusion of expert opinions suggests a balanced approach."
        
        return ConsensusResult(
            final_decision=final_decision,
            consensus_score=statistics.mean(weights),
            participating_agents=[op.agent_role for op in opinions],
            method_used=ConsensusMethod.BAYESIAN_FUSION,
            individual_opinions=opinions,
            reasoning="Bayesian information fusion based on confidence levels",
            confidence=statistics.mean([op.confidence for op in opinions])
        )
    
    def _expert_overrule_consensus(self, opinions: List[AgentOpinion]) -> ConsensusResult:
        """Expert overrule - highest authority agent wins"""
        
        # Find highest authority opinion (simplified - using confidence as proxy)
        expert_opinion = max(opinions, key=lambda op: op.confidence)
        
        return ConsensusResult(
            final_decision=expert_opinion.position,
            consensus_score=expert_opinion.confidence,
            participating_agents=[op.agent_role for op in opinions],
            method_used=ConsensusMethod.EXPERT_OVERRULE,
            individual_opinions=opinions,
            reasoning=f"Expert overrule by {expert_opinion.agent_role.value} (highest confidence)",
            confidence=expert_opinion.confidence,
            dissenting_opinions=[op for op in opinions if op != expert_opinion]
        )


class ConflictResolutionEngine:
    """Engine for resolving conflicts between agents"""
    
    def __init__(self, llm_orchestrator=None):
        self.llm_orchestrator = llm_orchestrator
    
    async def resolve_conflict(self, conflicting_opinions: List[AgentOpinion],
                              strategy: ConflictResolutionStrategy,
                              context: Dict[str, Any] = None) -> ConsensusResult:
        """
        Resolve conflicts between agents using specified strategy
        
        Args:
            conflicting_opinions: Conflicting agent opinions
            strategy: Resolution strategy to use
            context: Additional context for resolution
            
        Returns:
            ConsensusResult with conflict resolution
        """
        try:
            context = context or {}
            
            if strategy == ConflictResolutionStrategy.DEBATE:
                return await self._resolve_through_debate(conflicting_opinions, context)
            
            elif strategy == ConflictResolutionStrategy.EVIDENCE_BASED:
                return await self._resolve_evidence_based(conflicting_opinions, context)
            
            elif strategy == ConflictResolutionStrategy.AUTHORITY_BASED:
                return self._resolve_authority_based(conflicting_opinions)
            
            elif strategy == ConflictResolutionStrategy.COMPROMISE:
                return await self._resolve_through_compromise(conflicting_opinions, context)
            
            elif strategy == ConflictResolutionStrategy.ADDITIONAL_EXPERT:
                return await self._resolve_additional_expert(conflicting_opinions, context)
            
            else:
                # Default to evidence-based
                return await self._resolve_evidence_based(conflicting_opinions, context)
                
        except Exception as e:
            logger.error(f"Conflict resolution failed: {e}")
            return ConsensusResult(
                final_decision="Conflict resolution failed",
                consensus_score=0.0,
                participating_agents=[op.agent_role for op in conflicting_opinions],
                method_used=ConsensusMethod.MAJORITY_VOTE,  # Fallback
                individual_opinions=conflicting_opinions,
                reasoning=f"Resolution error: {str(e)}",
                confidence=0.0
            )
    
    async def _resolve_through_debate(self, opinions: List[AgentOpinion],
                                    context: Dict[str, Any]) -> ConsensusResult:
        """Resolve through structured debate"""
        
        if self.llm_orchestrator:
            debate_prompt = f"""
Facilitate a debate between the following conflicting expert opinions:

{chr(10).join([f"Agent {op.agent_role.value}: {op.position} (Confidence: {op.confidence:.2f})" for op in opinions])}

Context: {json.dumps(context, indent=2)}

As a neutral mediator, help resolve this conflict by:
1. Identifying the core disagreement
2. Evaluating the strength of each argument
3. Finding common ground
4. Proposing a resolution that addresses key concerns

Provide a balanced resolution that acknowledges valid points from all sides.
"""
            
            result = await self.llm_orchestrator.execute_task(
                agent_role="mediator",
                task_prompt=debate_prompt,
                task_type="conflict_resolution",
                context=context
            )
            
            if result.success:
                return ConsensusResult(
                    final_decision=result.result,
                    consensus_score=0.7,  # Moderate consensus from debate
                    participating_agents=[op.agent_role for op in opinions],
                    method_used=ConsensusMethod.MAJORITY_VOTE,
                    individual_opinions=opinions,
                    reasoning="Resolution through structured debate",
                    confidence=0.7
                )
        
        # Fallback to simple resolution
        return await self._resolve_through_compromise(opinions, context)
    
    async def _resolve_evidence_based(self, opinions: List[AgentOpinion],
                                    context: Dict[str, Any]) -> ConsensusResult:
        """Resolve based on evidence quality"""
        
        # Score opinions based on evidence quality
        evidence_scores = []
        for opinion in opinions:
            evidence_count = len(opinion.evidence) if opinion.evidence else 0
            evidence_score = min(1.0, evidence_count / 3.0)  # Normalize to max 3 pieces of evidence
            evidence_scores.append(evidence_score * opinion.confidence)
        
        # Select opinion with best evidence
        best_index = evidence_scores.index(max(evidence_scores))
        winning_opinion = opinions[best_index]
        
        return ConsensusResult(
            final_decision=winning_opinion.position,
            consensus_score=winning_opinion.confidence,
            participating_agents=[op.agent_role for op in opinions],
            method_used=ConsensusMethod.EXPERT_OVERRULE,
            individual_opinions=opinions,
            reasoning=f"Evidence-based resolution: {winning_opinion.agent_role.value} provided strongest evidence",
            confidence=winning_opinion.confidence,
            dissenting_opinions=[op for op in opinions if op != winning_opinion]
        )
    
    def _resolve_authority_based(self, opinions: List[AgentOpinion]) -> ConsensusResult:
        """Resolve based on agent authority"""
        
        # For simplicity, use confidence as proxy for authority
        # In full implementation, would use actual authority levels
        highest_authority_opinion = max(opinions, key=lambda op: op.confidence)
        
        return ConsensusResult(
            final_decision=highest_authority_opinion.position,
            consensus_score=highest_authority_opinion.confidence,
            participating_agents=[op.agent_role for op in opinions],
            method_used=ConsensusMethod.EXPERT_OVERRULE,
            individual_opinions=opinions,
            reasoning=f"Authority-based resolution: {highest_authority_opinion.agent_role.value} has highest authority",
            confidence=highest_authority_opinion.confidence,
            dissenting_opinions=[op for op in opinions if op != highest_authority_opinion]
        )
    
    async def _resolve_through_compromise(self, opinions: List[AgentOpinion],
                                        context: Dict[str, Any]) -> ConsensusResult:
        """Find a compromise solution"""
        
        if self.llm_orchestrator:
            compromise_prompt = f"""
Find a compromise solution that addresses the following conflicting expert opinions:

{chr(10).join([f"- {op.agent_role.value}: {op.position}" for op in opinions])}

Create a balanced compromise that:
1. Incorporates key elements from each position
2. Addresses main concerns raised by each expert
3. Provides a practical middle ground
4. Maintains the core value from each perspective

Provide a compromise solution that all experts could reasonably accept.
"""
            
            result = await self.llm_orchestrator.execute_task(
                agent_role="mediator",
                task_prompt=compromise_prompt,
                task_type="compromise_resolution",
                context=context
            )
            
            if result.success:
                return ConsensusResult(
                    final_decision=result.result,
                    consensus_score=0.6,  # Moderate consensus from compromise
                    participating_agents=[op.agent_role for op in opinions],
                    method_used=ConsensusMethod.WEIGHTED_AVERAGE,
                    individual_opinions=opinions,
                    reasoning="Resolution through compromise",
                    confidence=statistics.mean([op.confidence for op in opinions])
                )
        
        # Simple compromise fallback
        compromise_text = "A balanced approach incorporating insights from all expert perspectives."
        
        return ConsensusResult(
            final_decision=compromise_text,
            consensus_score=0.5,
            participating_agents=[op.agent_role for op in opinions],
            method_used=ConsensusMethod.WEIGHTED_AVERAGE,
            individual_opinions=opinions,
            reasoning="Simple compromise solution",
            confidence=statistics.mean([op.confidence for op in opinions])
        )
    
    async def _resolve_additional_expert(self, opinions: List[AgentOpinion],
                                       context: Dict[str, Any]) -> ConsensusResult:
        """Resolve by consulting an additional expert"""
        
        # For now, simulate additional expert consultation
        # In full implementation, would actually call another agent
        
        additional_expert_decision = "Based on additional expert consultation, a balanced approach is recommended that considers risk management while pursuing opportunities."
        
        return ConsensusResult(
            final_decision=additional_expert_decision,
            consensus_score=0.8,  # Higher confidence with additional input
            participating_agents=[op.agent_role for op in opinions] + [AgentRole.MEDIATOR],
            method_used=ConsensusMethod.EXPERT_OVERRULE,
            individual_opinions=opinions,
            reasoning="Resolution through additional expert consultation",
            confidence=0.8
        )


class EnhancedMultiAgentCoordinator:
    """Main coordinator for enhanced multi-agent workflows"""
    
    def __init__(self, 
                 multi_model_manager: MultiModelManager,
                 llm_orchestrator=None):
        
        self.mm_manager = multi_model_manager
        self.llm_orchestrator = llm_orchestrator
        
        # Initialize coordination components
        self.agent_selector = DynamicAgentSelector(llm_orchestrator)
        self.consensus_engine = ConsensusEngine(llm_orchestrator)
        self.conflict_resolver = ConflictResolutionEngine(llm_orchestrator)
        
        # Coordination state
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.coordination_history = []
        
        logger.info("Enhanced Multi-Agent Coordinator initialized")
    
    async def execute_coordinated_analysis(self,
                                         task: CoordinationTask,
                                         coordination_mode: CoordinationMode = CoordinationMode.CONSENSUS_BUILDING,
                                         max_agents: int = 5,
                                         consensus_method: ConsensusMethod = ConsensusMethod.WEIGHTED_AVERAGE
                                         ) -> Dict[str, Any]:
        """
        Execute coordinated analysis with intelligent agent selection and consensus building
        
        Args:
            task: Coordination task to execute
            coordination_mode: Mode of coordination
            max_agents: Maximum number of agents
            consensus_method: Method for building consensus
            
        Returns:
            Comprehensive coordination result
        """
        try:
            start_time = datetime.now()
            workflow_id = f"workflow_{start_time.strftime('%Y%m%d_%H%M%S')}_{task.task_id}"
            
            # Step 1: Intelligent agent selection
            selected_agents = await self.agent_selector.select_agents_for_task(task, max_agents)
            
            if not selected_agents:
                raise ValueError("No suitable agents found for the task")
            
            logger.info(f"Selected agents for {task.task_type}: {[agent.value for agent in selected_agents]}")
            
            # Step 2: Execute analysis with selected agents
            individual_results = await self._execute_individual_analyses(
                task, selected_agents
            )
            
            # Step 3: Build consensus from individual results
            opinions = self._extract_opinions(individual_results, selected_agents)
            
            consensus_result = await self.consensus_engine.build_consensus(
                opinions, 
                consensus_method,
                context={
                    'task': task.__dict__,
                    'agent_authorities': {
                        agent: self.agent_selector.agent_profiles[agent].authority_level
                        for agent in selected_agents
                    }
                }
            )
            
            # Step 4: Detect and resolve conflicts if necessary
            final_result = consensus_result
            if consensus_result.consensus_score < 0.6 and consensus_result.dissenting_opinions:
                logger.info("Low consensus detected, attempting conflict resolution")
                
                conflict_resolution = await self.conflict_resolver.resolve_conflict(
                    consensus_result.dissenting_opinions,
                    ConflictResolutionStrategy.DEBATE,
                    context={'original_consensus': consensus_result.__dict__}
                )
                
                # Update final result with conflict resolution
                final_result = conflict_resolution
            
            # Step 5: Generate comprehensive coordination report
            coordination_report = {
                'workflow_id': workflow_id,
                'task': task.__dict__,
                'coordination_mode': coordination_mode.value,
                'selected_agents': [agent.value for agent in selected_agents],
                'individual_results': individual_results,
                'consensus_result': final_result.__dict__,
                'execution_time': (datetime.now() - start_time).total_seconds(),
                'success': True,
                'timestamp': start_time
            }
            
            # Store in history
            self.coordination_history.append(coordination_report)
            
            # Update agent performance metrics
            await self._update_agent_performance(selected_agents, individual_results, final_result)
            
            logger.info(f"Coordinated analysis completed successfully: {workflow_id}")
            return coordination_report
            
        except Exception as e:
            logger.error(f"Coordinated analysis failed: {e}")
            return {
                'workflow_id': f"failed_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                'task': task.__dict__ if task else {},
                'error': str(e),
                'success': False,
                'timestamp': datetime.now()
            }
    
    async def _execute_individual_analyses(self, task: CoordinationTask,
                                         agents: List[AgentRole]) -> Dict[str, TaskResult]:
        """Execute individual analyses for each selected agent"""
        
        results = {}
        
        # Execute analyses in parallel for efficiency
        tasks_to_execute = []
        
        for agent in agents:
            # Create agent-specific prompt
            agent_prompt = self._create_agent_prompt(task, agent)
            
            # Create execution task
            execution_task = self.mm_manager.execute_task(
                agent_role=agent.value,
                task_prompt=agent_prompt,
                task_type=task.task_type,
                complexity_level=task.complexity_level,
                context=task.context
            )
            
            tasks_to_execute.append((agent, execution_task))
        
        # Execute all tasks
        for agent, execution_task in tasks_to_execute:
            try:
                if asyncio.iscoroutine(execution_task):
                    result = await execution_task
                else:
                    result = execution_task
                
                results[agent.value] = result
                
            except Exception as e:
                logger.error(f"Individual analysis failed for {agent.value}: {e}")
                # Create error result
                results[agent.value] = TaskResult(
                    result=f"Analysis failed: {str(e)}",
                    model_used=None,
                    execution_time=0,
                    actual_cost=0.0,
                    token_usage={},
                    success=False,
                    error_message=str(e)
                )
        
        return results
    
    def _create_agent_prompt(self, task: CoordinationTask, agent: AgentRole) -> str:
        """Create specialized prompt for each agent"""
        
        base_prompt = task.description
        
        # Add agent-specific context
        agent_profile = self.agent_selector.agent_profiles.get(agent)
        if agent_profile:
            specialization_prompt = f"""
As a {agent_profile.name}, please analyze the following from your area of expertise:

{base_prompt}

Your expertise areas include: {', '.join(agent_profile.expertise_domains)}

Please provide:
1. Your specialized analysis based on your expertise
2. Key insights relevant to your domain
3. Risks or opportunities you identify
4. Your confidence level in the analysis
5. Any recommendations specific to your area

Focus on what you do best while considering the broader context.
"""
        else:
            # Generic prompt if no profile
            specialization_prompt = f"Please analyze the following as a {agent.value}:\n\n{base_prompt}"
        
        return specialization_prompt
    
    def _extract_opinions(self, results: Dict[str, TaskResult], 
                         agents: List[AgentRole]) -> List[AgentOpinion]:
        """Extract structured opinions from analysis results"""
        
        opinions = []
        
        for agent in agents:
            if agent.value in results:
                result = results[agent.value]
                
                if result.success:
                    # Extract confidence from result or estimate
                    confidence = getattr(result, 'confidence_score', 0.8)
                    if confidence == 0:
                        confidence = 0.7  # Default confidence
                    
                    # Create opinion object
                    opinion = AgentOpinion(
                        agent_role=agent,
                        position=result.result,
                        confidence=confidence,
                        reasoning=result.result[:200] + "..." if len(result.result) > 200 else result.result,
                        evidence=[]  # Could extract from result content
                    )
                    
                    opinions.append(opinion)
        
        return opinions
    
    async def _update_agent_performance(self, agents: List[AgentRole],
                                      individual_results: Dict[str, TaskResult],
                                      final_result: ConsensusResult):
        """Update agent performance metrics"""
        
        # Simple performance update based on success and consensus alignment
        for agent in agents:
            if agent.value in individual_results:
                result = individual_results[agent.value]
                
                # Calculate metrics
                accuracy = 1.0 if result.success else 0.0
                response_time = result.execution_time
                collaboration_score = final_result.consensus_score  # How well they aligned with consensus
                confidence_calibration = 0.8  # Would need more sophisticated calculation
                
                # Update performance tracker
                self.agent_selector.performance_tracker.record_performance(
                    agent, accuracy, response_time, collaboration_score, confidence_calibration
                )
    
    def get_coordination_stats(self) -> Dict[str, Any]:
        """Get coordination system statistics"""
        
        if not self.coordination_history:
            return {
                'total_workflows': 0,
                'success_rate': 0.0,
                'avg_execution_time': 0.0,
                'agent_usage': {},
                'consensus_scores': []
            }
        
        successful_workflows = [w for w in self.coordination_history if w.get('success', False)]
        
        # Calculate statistics
        total_workflows = len(self.coordination_history)
        success_rate = len(successful_workflows) / total_workflows
        avg_execution_time = statistics.mean([w.get('execution_time', 0) for w in successful_workflows])
        
        # Agent usage statistics
        agent_usage = defaultdict(int)
        for workflow in self.coordination_history:
            for agent in workflow.get('selected_agents', []):
                agent_usage[agent] += 1
        
        # Consensus scores
        consensus_scores = []
        for workflow in successful_workflows:
            consensus_result = workflow.get('consensus_result', {})
            if 'consensus_score' in consensus_result:
                consensus_scores.append(consensus_result['consensus_score'])
        
        return {
            'total_workflows': total_workflows,
            'success_rate': success_rate,
            'avg_execution_time': avg_execution_time,
            'agent_usage': dict(agent_usage),
            'consensus_scores': consensus_scores,
            'avg_consensus_score': statistics.mean(consensus_scores) if consensus_scores else 0.0,
            'agent_performance': {
                agent.value: self.agent_selector.performance_tracker.get_agent_score(agent)
                for agent in AgentRole
            }
        }


# Utility functions for creating common coordination tasks
def create_market_analysis_task(symbol: str, analysis_type: str = "comprehensive") -> CoordinationTask:
    """Create a market analysis coordination task"""
    
    return CoordinationTask(
        task_id=f"market_analysis_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        task_type="market_analysis",
        description=f"Comprehensive market analysis for {symbol}",
        context={
            'symbol': symbol,
            'analysis_type': analysis_type,
            'domains': ['technical', 'fundamental', 'sentiment', 'risk']
        },
        required_capabilities=['financial_analysis', 'market_analysis'],
        complexity_level="high",
        priority=0.8
    )


def create_risk_assessment_task(symbols: List[str], portfolio_context: Dict[str, Any] = None) -> CoordinationTask:
    """Create a risk assessment coordination task"""
    
    return CoordinationTask(
        task_id=f"risk_assessment_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        task_type="risk_assessment",
        description=f"Risk assessment for portfolio containing {', '.join(symbols)}",
        context={
            'symbols': symbols,
            'portfolio_context': portfolio_context or {},
            'domains': ['risk', 'portfolio', 'volatility']
        },
        required_capabilities=['risk_assessment', 'portfolio_analysis'],
        complexity_level="high",
        priority=0.9
    )