import React, { useState } from 'react';
import { Box, Grid, Paper, Typography, Button, Select, MenuItem, FormControl, CircularProgress, Tabs, Tab } from '@mui/material';
import { PlayArrow, Assessment, Chat, History } from '@mui/icons-material';
import EditorPanel from './EditorPanel';
import ResultsPanel from './ResultsPanel';
import HistoryPanel from './HistoryPanel';
import ChatPanel from './ChatPanel';
import axios from 'axios';

// Types
import type { AnalysisResult, HistoryItem, ChatMessage } from '../../types';

const Workbench: React.FC = () => {
    const [code, setCode] = useState<string>('// Write your code here...\n\nfunction example() {\n  console.log("Hello CodeGuard!");\n}');
    const [language, setLanguage] = useState<string>('javascript');
    const [isAnalyzing, setIsAnalyzing] = useState(false);
    const [results, setResults] = useState<AnalysisResult | null>(null);
    const [activeLine, setActiveLine] = useState<number | null>(null);
    const [history, setHistory] = useState<HistoryItem[]>([]);

    // Chat State
    const [activeTab, setActiveTab] = useState(0);
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
    const [isChatLoading, setIsChatLoading] = useState(false);

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
        setActiveTab(0); // Switch to results tab
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

    const handleSendMessage = async (message: string) => {
        const newMessage: ChatMessage = {
            id: Date.now().toString(),
            role: 'user',
            content: message,
            timestamp: Date.now()
        };
        setChatMessages(prev => [...prev, newMessage]);
        setIsChatLoading(true);

        try {
            const response = await axios.post('http://localhost:8000/api/v2/chat', {
                code,
                language,
                message,
                context: chatMessages.map(m => ({ role: m.role, content: m.content })),
                analysis_result: results
            });

            const botMessage: ChatMessage = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: response.data.reply,
                timestamp: Date.now()
            };
            setChatMessages(prev => [...prev, botMessage]);
        } catch (error) {
            console.error('Chat failed:', error);
            // Add error message
            setChatMessages(prev => [...prev, {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: "Sorry, I encountered an error processing your request.",
                timestamp: Date.now()
            }]);
        } finally {
            setIsChatLoading(false);
        }
    };

    const handleIssueClick = (line: number) => {
        setActiveLine(line);
    };

    const handleRestoreHistory = (item: HistoryItem) => {
        setCode(item.code);
        setLanguage(item.language);
        setResults(item);
        setActiveTab(0); // Switch to results
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

                {/* Right Sidebar (Tabs: Results, Chat, History) */}
                <Grid size={{ xs: 12, lg: 6 }} sx={{ height: '100%' }}>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, height: '100%' }}>

                        {/* Tabs */}
                        <Paper className="glass-panel" sx={{ borderRadius: 3 }}>
                            <Tabs
                                value={activeTab}
                                onChange={(_, newValue) => setActiveTab(newValue)}
                                variant="fullWidth"
                                sx={{ minHeight: 48 }}
                            >
                                <Tab icon={<Assessment fontSize="small" />} iconPosition="start" label="Results" />
                                <Tab icon={<Chat fontSize="small" />} iconPosition="start" label="Chat" />
                                <Tab icon={<History fontSize="small" />} iconPosition="start" label="History" />
                            </Tabs>
                        </Paper>

                        {/* Tab Content */}
                        <Box sx={{ flexGrow: 1, minHeight: 0, position: 'relative' }}>
                            {/* Results Tab */}
                            <Box sx={{
                                display: activeTab === 0 ? 'block' : 'none',
                                height: '100%'
                            }}>
                                <ResultsPanel
                                    results={results}
                                    isAnalyzing={isAnalyzing}
                                    onIssueClick={handleIssueClick}
                                />
                            </Box>

                            {/* Chat Tab */}
                            <Box sx={{
                                display: activeTab === 1 ? 'block' : 'none',
                                height: '100%'
                            }}>
                                <ChatPanel
                                    messages={chatMessages}
                                    onSendMessage={handleSendMessage}
                                    isLoading={isChatLoading}
                                />
                            </Box>

                            {/* History Tab */}
                            <Box sx={{
                                display: activeTab === 2 ? 'block' : 'none',
                                height: '100%'
                            }}>
                                <HistoryPanel
                                    history={history}
                                    onRestore={handleRestoreHistory}
                                    onDelete={handleDeleteHistory}
                                />
                            </Box>
                        </Box>
                    </Box>
                </Grid>
            </Grid>
        </Box>
    );
};

export default Workbench;
