import React from 'react';
import { Box, Card, CardContent, Typography, Chip, Stack, CircularProgress, Alert } from '@mui/material';
import { Security, Assessment, Speed, AutoFixHigh, BugReport } from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import { AnalysisResult } from './Workbench';

interface ResultsPanelProps {
    results: AnalysisResult | null;
    isAnalyzing: boolean;
    onIssueClick: (line: number) => void;
}

const ResultsPanel: React.FC<ResultsPanelProps> = ({ results, isAnalyzing, onIssueClick }) => {

    const getSeverityColor = (severity: string) => {
        switch (severity) {
            case 'critical': return '#ef4444';
            case 'high': return '#f97316';
            case 'medium': return '#eab308';
            case 'low': return '#3b82f6';
            default: return '#94a3b8';
        }
    };

    return (
        <Paper
            className="glass-panel"
            sx={{
                height: '100%',
                overflow: 'hidden',
                borderRadius: 3,
                display: 'flex',
                flexDirection: 'column',
                bgcolor: 'rgba(15, 23, 42, 0.3)'
            }}
        >
            <Box sx={{ flexGrow: 1, overflowY: 'auto', p: 3 }}>
                <AnimatePresence mode="wait">
                    {isAnalyzing ? (
                        <motion.div
                            key="loading"
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}
                        >
                            <CircularProgress size={48} sx={{ mb: 2 }} />
                            <Typography variant="h6" color="text.secondary">Analyzing Code...</Typography>
                            <Typography variant="body2" color="text.secondary">Running AI security & quality scan</Typography>
                        </motion.div>
                    ) : !results ? (
                        <motion.div
                            key="empty"
                            initial={{ opacity: 0, y: 20 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -20 }}
                            style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.7 }}
                        >
                            <AutoFixHigh sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
                            <Typography variant="h6" color="text.secondary">Ready to Analyze</Typography>
                            <Typography variant="body2" color="text.secondary">Run a comprehensive scan to see results here.</Typography>
                        </motion.div>
                    ) : (
                        <Stack spacing={3} component={motion.div} initial={{ opacity: 0 }} animate={{ opacity: 1 }}>

                            {/* Summary Cards */}
                            <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 2 }}>
                                <Card className="glass-card" sx={{ borderRadius: 3, p: 1.5 }}>
                                    <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                                        <Security fontSize="small" color="error" />
                                        <Typography variant="caption" fontWeight={600}>Security</Typography>
                                    </Stack>
                                    <Typography variant="h4" fontWeight={700}>{results.summary.security_score}</Typography>
                                </Card>
                                <Card className="glass-card" sx={{ borderRadius: 3, p: 1.5 }}>
                                    <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                                        <Assessment fontSize="small" color="warning" />
                                        <Typography variant="caption" fontWeight={600}>Quality</Typography>
                                    </Stack>
                                    <Typography variant="h4" fontWeight={700}>{results.summary.quality_score}</Typography>
                                </Card>
                                <Card className="glass-card" sx={{ borderRadius: 3, p: 1.5 }}>
                                    <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
                                        <Speed fontSize="small" color="success" />
                                        <Typography variant="caption" fontWeight={600}>Perf</Typography>
                                    </Stack>
                                    <Typography variant="h4" fontWeight={700}>{results.summary.performance_score}</Typography>
                                </Card>
                            </Box>

                            {/* AI Detection Alert */}
                            {results.ai_detection.is_ai_generated && (
                                <Alert
                                    severity="warning"
                                    variant="filled"
                                    sx={{ borderRadius: 2, bgcolor: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', border: '1px solid rgba(245, 158, 11, 0.3)' }}
                                >
                                    <Typography variant="subtitle2" fontWeight={700}>AI-Generated Code Detected</Typography>
                                    <Typography variant="body2">
                                        Probability: {results.ai_detection.probability}% (Confidence: {results.ai_detection.confidence}%)
                                    </Typography>
                                </Alert>
                            )}

                            {/* Issues List */}
                            <Box>
                                <Typography variant="h6" sx={{ fontWeight: 700, mb: 2 }}>Detected Issues ({results.issues.length})</Typography>
                                <Stack spacing={2}>
                                    {results.issues.map((issue, index) => (
                                        <motion.div
                                            key={issue.id}
                                            initial={{ opacity: 0, x: 20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            transition={{ delay: index * 0.05 }}
                                        >
                                            <Card
                                                className="glass-card"
                                                onClick={() => onIssueClick(issue.line)}
                                                sx={{
                                                    borderRadius: 3,
                                                    cursor: 'pointer',
                                                    transition: 'all 0.2s',
                                                    '&:hover': { transform: 'translateY(-2px)', bgcolor: 'rgba(255,255,255,0.05)' }
                                                }}
                                            >
                                                <CardContent sx={{ p: 2, '&:last-child': { pb: 2 } }}>
                                                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                                        <Chip
                                                            label={issue.severity.toUpperCase()}
                                                            size="small"
                                                            sx={{
                                                                height: 20,
                                                                fontSize: '0.7rem',
                                                                fontWeight: 700,
                                                                bgcolor: `${getSeverityColor(issue.severity)}20`,
                                                                color: getSeverityColor(issue.severity)
                                                            }}
                                                        />
                                                        <Typography variant="caption" sx={{ fontFamily: 'monospace', color: 'text.secondary' }}>
                                                            Ln {issue.line}
                                                        </Typography>
                                                    </Box>
                                                    <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 0.5 }}>
                                                        {issue.title}
                                                    </Typography>
                                                    <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5, fontSize: '0.85rem' }}>
                                                        {issue.description}
                                                    </Typography>
                                                    {issue.suggestion && (
                                                        <Box sx={{ bgcolor: 'rgba(0,0,0,0.2)', p: 1, borderRadius: 1, borderLeft: '2px solid #3b82f6' }}>
                                                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>Suggestion:</Typography>
                                                            <Typography variant="body2" sx={{ fontSize: '0.85rem' }}>{issue.suggestion}</Typography>
                                                        </Box>
                                                    )}
                                                </CardContent>
                                            </Card>
                                        </motion.div>
                                    ))}
                                </Stack>
                            </Box>

                        </Stack>
                    )}
                </AnimatePresence>
            </Box>
        </Paper>
    );
};

import { Paper } from '@mui/material'; // Fixed missing import
export default ResultsPanel;
