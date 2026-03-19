# run_agent.py
from agent import OprimionAnalysisAgent
import sys

if __name__ == "__main__":
    product_id = sys.argv[1] if len(sys.argv) > 1 else "default_product"
    agent = OprimionAnalysisAgent()
    agent.run_once(product_id, hours=24)
