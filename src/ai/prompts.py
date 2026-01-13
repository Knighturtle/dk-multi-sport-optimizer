import json

def make_slate_summary_prompt(analysis_text: str, language: str = "English") -> str:
    """
    Constructs a prompt to summarize the slate state.
    """
    if language == "日本語":
        return f"""
    あなたはプロのDFSアナリストです。
    提供されたデータをもとに、現在のスレート（試合日程）の状況を分析してください。
    
    データ:
    {analysis_text}
    
    タスク:
    1. **バリュー分析**: コストパフォーマンスが良い選手（Top Value）を評価してください。
    2. **GPP戦略 (Chalk vs Leverage)**:
       - 人気選手（Chalk）のリスク（過度な人気など）を指摘してください。
       - 差別化できる「隠れた名選手（Leverage）」を具体的に推奨してください。
    3. **チーム戦略**: どのチームを中心にスタック（複数採用）すべきか考察してください。
    4. **アクションプラン**: GPPで勝つための具体的な設定指針（例：「Chalk選手は1人まで」「〇〇チームのスタックを狙う」）を提示してください。
    
    回答は日本語で行ってください。
    """
    else:
        return f"""
    You are a professional DFS analyst.
    Analyze the current slate situation based on the provided data.
        
    DATA:
    {analysis_text}
        
    TASK:
    1. **Value Analysis**: Identify the best value plays (ROI).
    2. **GPP Strategy (Chalk vs Leverage)**:
       - Assess the risks of the highest owned players (Chalk).
       - Recommend specific low-owned pivots (Leverage) with upside.
    3. **Stacking Strategy**: Which teams are best to stack?
    4. **Action Plan**: Specific advice for optimizer settings (e.g., "Limit Chalk to 1", "Stack Team X").
        
    Respond in English ONLY. Be concise and actionable.
    """

def make_edge_finder_prompt(analysis_text: str, language: str = "English") -> str:
    """
    Prompt to find specific edges/hypotheses.
    """
    if language == "日本語":
        return f"""
        データ:
        {analysis_text}
        
        タスク:
        このスレートにおける「市場の盲点（Edge）」を3つ特定してください。
        大衆が見逃しそうな、しかし高いアップサイドを持つシナリオや選手を挙げてください。
        
        回答は日本語で行ってください。
        """
    else:
        return f"""
        DATA:
        {analysis_text}
        
        TASK:
        Identify 3 specific "Market Edges" or contrarian hypotheses for this slate.
        Focus on scenarios or players that the field might overlook but have high GPP upside.
        
        Respond in English ONLY.
        """

def make_lineup_critique_prompt(lineup_data: dict, analysis_text: str, language: str = "English") -> str:
    """
    Critiques a specific lineup.
    """
    lu_str = json.dumps(lineup_data, indent=2, ensure_ascii=False)
    
    if language == "日本語":
        return f"""
        以下のラインナップを厳しく批評してください。
        
        ラインナップ:
        {lu_str}
        
        背景データ:
        {analysis_text}
        
        タスク:
        1. 強み（積算プロジェクション、相関など）
        2. 弱み（Chalk過多、アップサイド不足など）
        3. 改善提案
        
        回答は日本語で行ってください。
        """
    else:
        return f"""
        Critique the following DFS lineup in the context of the slate.
        
        LINEUP:
        {lu_str}
        
        CONTEXT:
        {analysis_text}
        
        TASK:
        1. Strengths (Projection, Correlation, Stack)
        2. Weaknesses (Too much Chalk, Low Ceiling, etc.)
        3. Improvement Suggestions
        
        Respond in English ONLY.
        """

def make_strategy_coach_prompt(settings_data: dict, analysis_text: str, language: str = "English") -> str:
    """
    Suggests optimizer settings changes.
    """
    set_str = json.dumps(settings_data, indent=2, ensure_ascii=False)
    
    if language == "日本語":
        return f"""
        現在の設定:
        {set_str}
        
        スレート状況:
        {analysis_text}
        
        タスク:
        オプティマイザーの設定（GPPモード）についてアドバイスしてください。
        - ターゲットとすべき「平均Ownership」
        - 推奨する「スタック設定」
        - Chalkの許容人数
        
        回答は日本語で行ってください。
        """
    else:
        return f"""
        Current Settings:
        {set_str}
        
        Slate Context:
        {analysis_text}
        
        TASK:
        Suggest specific Optimizer Settings for a GPP contest.
        - Target Average Ownership
        - Recommended Stacking Configuration
        - Max Chalk Players allowed
        
        Respond in English ONLY.
        """
