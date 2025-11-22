export interface AnalysisResult {
    summary: {
        security_score: number;
        quality_score: number;
        performance_score: number;
        total_issues: number;
        critical_issues: number;
    };
    issues: Array<{
        id: string;
        type: 'security' | 'quality' | 'performance';
        severity: 'critical' | 'high' | 'medium' | 'low';
        title: string;
        description: string;
        line: number;
        suggestion: string;
    }>;
    ai_detection: {
        is_ai_generated: boolean;
        probability: number;
        confidence: number;
    };
    language: string;
}

export interface HistoryItem extends AnalysisResult {
    id: string;
    timestamp: number;
    code: string;
}
