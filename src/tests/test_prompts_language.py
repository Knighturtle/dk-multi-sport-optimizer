import sys
import os
sys.path.append(os.path.join(os.getcwd(), "src"))

from ai.prompts import make_slate_summary_prompt, make_edge_finder_prompt, make_strategy_coach_prompt, make_lineup_critique_prompt

def test_prompts_language():
    print("Testing Language Support in Prompts...")
    
    context = "Player A: $5000, Proj 30"
    
    # 1. Slate Summary
    p_en = make_slate_summary_prompt(context, "English")
    if "Respond in English ONLY" not in p_en:
        print("FAIL: English Summary Prompt missing directive")
        sys.exit(1)
    if "日本語" in p_en:
         print("FAIL: English Summary Prompt contains Japanese")
         sys.exit(1)
         
    p_ja = make_slate_summary_prompt(context, "日本語")
    if "回答は日本語で行ってください" not in p_ja:
         print("FAIL: Japanese Summary Prompt missing directive")
         sys.exit(1)
         
    # 2. Edge Finder
    p_edge_en = make_edge_finder_prompt(context, "English")
    if "Market Edges" not in p_edge_en:
        print("FAIL: English Edge Prompt missing keyword")
        sys.exit(1)
        
    p_edge_ja = make_edge_finder_prompt(context, "日本語")
    if "市場の盲点" not in p_edge_ja:
        print("FAIL: Japanese Edge Prompt missing keyword")
        sys.exit(1)
        
    print("PASS: Prompt Language Checks")

if __name__ == "__main__":
    test_prompts_language()
