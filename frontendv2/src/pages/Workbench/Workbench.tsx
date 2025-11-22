import React, { useState } from 'react';
import { Box, Grid, Paper, Typography, Button, Select, MenuItem, FormControl, CircularProgress } from '@mui/material';
import { PlayArrow } from '@mui/icons-material';
import EditorPanel from './EditorPanel';
import ResultsPanel from './ResultsPanel';
import HistoryPanel from './HistoryPanel';
import axios from 'axios';

// Types
import type { AnalysisResult, HistoryItem } from '../../types';

const Workbench: React.FC = () => {
    const [code, setCode] = useState<string>('// Write your code here...\n\nfunction example() {\n  console.log("Hello CodeGuard!");\n}');
    const [language, setLanguage] = useState<string>('javascript');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [results, setResults] = useState<AnalysisResult | null>(null);
    const [activeLine, setActiveLine] = useState<number | null>(null);
    const [history, setHistory] = useState<HistoryItem[]>([]);

    // Load history from local storage on mount
    React.useEffect(() => {
        const savedHistory = localStorage.getItem('codeguard_history');
        if (savedHistory) {
            try {
                setHistory(JSON.parse(savedHistory));
            } catch (e) {
                console.error('Failed to parse history:', e);
            }
        }

        // Check for restore target
        const restoreTarget = localStorage.getItem('codeguard_restore_target');
        if (restoreTarget) {
            try {
                const item = JSON.parse(restoreTarget);
                setCode(item.code);
                setLanguage(item.language);
                setResults(item);
                localStorage.removeItem('codeguard_restore_target'); // Clear it
            } catch (e) {
                console.error('Failed to restore target:', e);
            }
        }
    }, []);

    // Save history to local storage whenever it changes
    React.useEffect(() => {
        localStorage.setItem('codeguard_history', JSON.stringify(history));
    }, [history]);

    const handleAnalyze = async () => {
        setIsAnalyzing(true);
        setResults(null); // Reset results
        try {
            const response = await axios.post('http://localhost:8000/api/v2/analyze', {
                code,
                language
            });
            const result = response.data;
            setResults(result);

            // Add to history
            const newHistoryItem: HistoryItem = {
                ...result,
                id: Date.now().toString(),
                timestamp: Date.now(),
                code: code // Save the code snapshot
            };
            setHistory(prev => [newHistoryItem, ...prev]);

        } catch (error) {
            console.error('Analysis failed:', error);
            // TODO: Show error toast
        } finally {
            setIsAnalyzing(false);
        }
    };

    const handleIssueClick = (line: number) => {
        setActiveLine(line);
    };

    const handleRestoreHistory = (item: HistoryItem) => {
        setCode(item.code);
        setLanguage(item.language);
        setResults(item);
    };

    const handleDeleteHistory = (id: string) => {
        setHistory(prev => prev.filter(item => item.id !== id));
    };

    return (
        <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Toolbar */}
            <Paper
                className="glass-panel"
                sx={{
                    p: 1.5,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    borderRadius: 3
                }}
            >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Typography variant="h6" sx={{ fontWeight: 700, ml: 1 }}>Workbench</Typography>
                    <FormControl size="small" sx={{ minWidth: 140 }}>
                        <Select
                            value={language}
                            onChange={(e) => setLanguage(e.target.value)}
                            sx={{ height: 36, borderRadius: 2 }}
                        >
                            <MenuItem value="javascript">JavaScript</MenuItem>
                            <MenuItem value="typescript">TypeScript</MenuItem>
                            <MenuItem value="python">Python</MenuItem>
                            <MenuItem value="java">Java</MenuItem>
                            <MenuItem value="cpp">C++</MenuItem>
                        </Select>
                    </FormControl>
                </Box>

                <Button
                    variant="contained"
                    startIcon={isAnalyzing ? <CircularProgress size={18} color="inherit" /> : <PlayArrow />}
                    onClick={handleAnalyze}
                    disabled={isAnalyzing}
                    sx={{ px: 3 }}
                >
                    {isAnalyzing ? 'Analyzing...' : 'Run Analysis'}
                </Button>
            </Paper>

            {/* Split View */}
            <Grid container spacing={2} sx={{ flexGrow: 1, minHeight: 0 }}>
                {/* Editor Panel */}
                <Grid size={{ xs: 12, lg: 6 }} sx={{ height: '100%' }}>
                    <EditorPanel
                        code={code}
                        language={language}
                        onChange={setCode}
                        activeLine={activeLine}
                    />
                </Grid>

                {/* Right Sidebar (Results + History) */}
                <Grid size={{ xs: 12, lg: 6 }} sx={{ height: '100%' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%' }}>
                        {/* Results Panel */}
                        <Box sx={{ flexGrow: 1, minHeight: 0, flexBasis: '60%' }}>
                            <ResultsPanel
                                results={results}
                                isAnalyzing={isAnalyzing}
                                onIssueClick={handleIssueClick}
                            />
                        </Box>

                        {/* History Panel */}
                        <Box sx={{ flexGrow: 1, minHeight: 0, flexBasis: '40%' }}>
                            <HistoryPanel
                                history={history}
                                onRestore={handleRestoreHistory}
                                onDelete={handleDeleteHistory}
                            />
                        </Box>
                    </Box>
                </Grid>
            </Grid>
        </Box>
    );
};

export default Workbench;
