import React, { useState, useEffect } from 'react';
import { Box, Paper, Typography, Container, Grid, Button, IconButton, Chip, Stack, Dialog, DialogTitle, DialogContent, DialogActions } from '@mui/material';
import { Delete, Restore, ArrowBack, History as HistoryIcon, Security, Assessment, Speed, AutoFixHigh } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import type { HistoryItem } from '../../types';

const History: React.FC = () => {
    const navigate = useNavigate();
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const [deleteId, setDeleteId] = useState<string | null>(null);

    useEffect(() => {
        const savedHistory = localStorage.getItem('codeguard_history');
        if (savedHistory) {
            try {
                setHistory(JSON.parse(savedHistory));
            } catch (e) {
                console.error('Failed to parse history:', e);
            }
        }
    }, []);

    const handleDelete = () => {
        if (deleteId) {
            const newHistory = history.filter(item => item.id !== deleteId);
            setHistory(newHistory);
            localStorage.setItem('codeguard_history', JSON.stringify(newHistory));
            setDeleteId(null);
        }
    };

    const handleRestore = (item: HistoryItem) => {
        // We can't easily pass state to Workbench via route without context or URL params.
        // For now, let's copy to clipboard or just navigate back and let user know.
        // Ideally, Workbench should read "current" from a shared store or URL.
        // A simple hack: save "restore_target" to local storage and Workbench reads it on mount.
        localStorage.setItem('codeguard_restore_target', JSON.stringify(item));
        navigate('/workbench');
    };

    const formatDate = (timestamp: number) => {
        return new Date(timestamp).toLocaleString(undefined, {
            weekday: 'short', year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
    };

    return (
        <Container maxWidth="lg" sx={{ py: 4, height: '100%', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button
                    startIcon={<ArrowBack />}
                    onClick={() => navigate('/workbench')}
                    sx={{ color: 'text.secondary' }}
                >
                    Back to Workbench
                </Button>
                <Typography variant="h4" fontWeight={700} sx={{ flexGrow: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
                    <HistoryIcon fontSize="large" color="primary" />
                    Analysis History
                </Typography>
                <Chip label={`${history.length} Scans`} color="primary" variant="outlined" />
            </Box>

            <Paper
                className="glass-panel"
                sx={{
                    flexGrow: 1,
                    bgcolor: 'rgba(15, 23, 42, 0.3)',
                    borderRadius: 3,
                    overflow: 'hidden',
                    display: 'flex',
                    flexDirection: 'column'
                }}
            >
                {history.length === 0 ? (
                    <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.5 }}>
                        <HistoryIcon sx={{ fontSize: 64, mb: 2 }} />
                        <Typography variant="h6">No history found</Typography>
                        <Typography variant="body2">Run an analysis in the Workbench to see it here.</Typography>
                    </Box>
                ) : (
                    <Box sx={{ overflowY: 'auto', p: 3 }}>
                        <Grid container spacing={2}>
                            <AnimatePresence>
                                {history.map((item) => (
                                    <Grid size={{ xs: 12 }} key={item.id} component={motion.div} layout initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, scale: 0.9 }}>
                                        <Paper
                                            className="glass-card"
                                            sx={{
                                                p: 2.5,
                                                borderRadius: 2,
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: 3,
                                                transition: 'transform 0.2s',
                                                '&:hover': { transform: 'translateY(-2px)', bgcolor: 'rgba(255,255,255,0.03)' }
                                            }}
                                        >
                                            <Box sx={{ minWidth: 120 }}>
                                                <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 0.5 }}>
                                                    {formatDate(item.timestamp)}
                                                </Typography>
                                                <Chip
                                                    label={item.language}
                                                    size="small"
                                                    sx={{ textTransform: 'capitalize', fontWeight: 600 }}
                                                />
                                            </Box>

                                            <Stack direction="row" spacing={3} sx={{ flexGrow: 1 }}>
                                                <Box>
                                                    <Stack direction="row" alignItems="center" spacing={1}>
                                                        <Security fontSize="small" color={item.summary.security_score >= 90 ? 'success' : 'error'} />
                                                        <Typography variant="body2" color="text.secondary">Security</Typography>
                                                    </Stack>
                                                    <Typography variant="h6" fontWeight={700}>{item.summary.security_score}</Typography>
                                                </Box>
                                                <Box>
                                                    <Stack direction="row" alignItems="center" spacing={1}>
                                                        <Assessment fontSize="small" color="warning" />
                                                        <Typography variant="body2" color="text.secondary">Quality</Typography>
                                                    </Stack>
                                                    <Typography variant="h6" fontWeight={700}>{item.summary.quality_score}</Typography>
                                                </Box>
                                                <Box>
                                                    <Stack direction="row" alignItems="center" spacing={1}>
                                                        <Speed fontSize="small" color="info" />
                                                        <Typography variant="body2" color="text.secondary">Perf</Typography>
                                                    </Stack>
                                                    <Typography variant="h6" fontWeight={700}>{item.summary.performance_score}</Typography>
                                                </Box>
                                                <Box>
                                                    <Stack direction="row" alignItems="center" spacing={1}>
                                                        <AutoFixHigh fontSize="small" color="secondary" />
                                                        <Typography variant="body2" color="text.secondary">Issues</Typography>
                                                    </Stack>
                                                    <Typography variant="h6" fontWeight={700}>{item.summary.total_issues}</Typography>
                                                </Box>
                                            </Stack>

                                            <Stack direction="row" spacing={1}>
                                                <Button
                                                    variant="outlined"
                                                    size="small"
                                                    startIcon={<Restore />}
                                                    onClick={() => handleRestore(item)}
                                                >
                                                    Restore
                                                </Button>
                                                <IconButton
                                                    color="error"
                                                    size="small"
                                                    onClick={() => setDeleteId(item.id)}
                                                >
                                                    <Delete />
                                                </IconButton>
                                            </Stack>
                                        </Paper>
                                    </Grid>
                                ))}
                            </AnimatePresence>
                        </Grid>
                    </Box>
                )}
            </Paper>

            <Dialog open={!!deleteId} onClose={() => setDeleteId(null)}>
                <DialogTitle>Delete Analysis?</DialogTitle>
                <DialogContent>
                    <Typography>Are you sure you want to delete this analysis record? This action cannot be undone.</Typography>
                </DialogContent>
                <DialogActions>
                    <Button onClick={() => setDeleteId(null)}>Cancel</Button>
                    <Button onClick={handleDelete} color="error" variant="contained">Delete</Button>
                </DialogActions>
            </Dialog>
        </Container>
    );
};

export default History;
