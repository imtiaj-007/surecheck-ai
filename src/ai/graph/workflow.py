from langgraph.graph import END, START, StateGraph

from src.ai.agent.bill_agent import bill_extraction_node
from src.ai.agent.claim_agent import claim_validation_node
from src.ai.agent.classification_agent import classification_node
from src.ai.agent.discharge_agent import discharge_extraction_node
from src.ai.agent.id_agent import id_extraction_node

from .state import ClaimState

# 1. Initialize the Graph
workflow = StateGraph(ClaimState)

# 2. Add Nodes
workflow.add_node("classifier", classification_node)
workflow.add_node("bill_extractor", bill_extraction_node)
workflow.add_node("discharge_extractor", discharge_extraction_node)
workflow.add_node("id_extractor", id_extraction_node)
workflow.add_node("claim_validator", claim_validation_node)

# 3. Define Edges

# Start -> Classifier
workflow.add_edge(START, "classifier")

# Classifier -> Parallel Extraction
workflow.add_edge("classifier", "bill_extractor")
workflow.add_edge("classifier", "discharge_extractor")
workflow.add_edge("classifier", "id_extractor")

# Extractors -> Validator
workflow.add_edge("bill_extractor", "claim_validator")
workflow.add_edge("discharge_extractor", "claim_validator")
workflow.add_edge("id_extractor", "claim_validator")

# Validator -> End
workflow.add_edge("claim_validator", END)

# 4. Compile
app = workflow.compile()
