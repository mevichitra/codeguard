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
        detected_patterns?: string[];
        reasoning?: string;
    };
    metrics?: {
        security: {
            cwe_ids: string[];
            cvss_score: number;
        };
        quality: {
            cyclomatic_complexity: number;
            maintainability_index: number;
            code_smells: string[];
        };
        performance: {
            time_complexity: string;
            space_complexity: string;
            resource_usage: string;
        };
    };
    language: string;
}

export interface HistoryItem extends AnalysisResult {
    id: string;
    timestamp: number;
    code: string;
}
