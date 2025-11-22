import React, { useState } from 'react';
import { Box, Grid, Paper, Typography, Button, Select, MenuItem, FormControl, CircularProgress } from '@mui/material';
import { PlayArrow } from '@mui/icons-material';
import EditorPanel from './EditorPanel';
import ResultsPanel from './ResultsPanel';
import axios from 'axios';

// Types
import type { AnalysisResult } from '../../types';

const Workbench: React.FC = () => {
    const [code, setCode] = useState<string>('// Write your code here...\n\nfunction example() {\n  console.log("Hello CodeGuard!");\n}');
    const [language, setLanguage] = useState<string>('javascript');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [results, setResults] = useState<AnalysisResult | null>(null);
    const [activeLine, setActiveLine] = useState<number | null>(null);

    const handleAnalyze = async () => {
        setIsAnalyzing(true);
        setResults(null); // Reset results
        try {
            const response = await axios.post('http://localhost:8000/api/v2/analyze', {
                code,
                language
            });
            setResults(response.data);
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
                <Grid size={{ xs: 12, lg: 7 }} sx={{ height: '100%' }}>
                    <EditorPanel
                        code={code}
                        language={language}
                        onChange={setCode}
                        activeLine={activeLine}
                    />
                </Grid>

                {/* Results Panel */}
                <Grid size={{ xs: 12, lg: 5 }} sx={{ height: '100%' }}>
                    <ResultsPanel
                        results={results}
                        isAnalyzing={isAnalyzing}
                        onIssueClick={handleIssueClick}
                    />
                </Grid>
            </Grid>
        </Box>
    );
};

export default Workbench;
