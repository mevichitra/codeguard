import React from 'react';
import { Box, Paper, Typography, IconButton, List, ListItem, ListItemText, Chip, Stack, Tooltip } from '@mui/material';
import { Delete, Restore, History as HistoryIcon, AccessTime } from '@mui/icons-material';
import { motion, AnimatePresence } from 'framer-motion';
import type { HistoryItem } from '../../types';

interface HistoryPanelProps {
    history: HistoryItem[];
    onRestore: (item: HistoryItem) => void;
    onDelete: (id: string) => void;
}

const HistoryPanel: React.FC<HistoryPanelProps> = ({ history, onRestore, onDelete }) => {

    const formatDate = (timestamp: number) => {
        return new Date(timestamp).toLocaleString(undefined, {
            month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
        });
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
            <Box sx={{ p: 2, borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', alignItems: 'center', gap: 1 }}>
                <HistoryIcon color="action" />
                <Typography variant="h6" fontWeight={700}>History</Typography>
                <Chip label={history.length} size="small" sx={{ ml: 'auto', bgcolor: 'rgba(255,255,255,0.1)' }} />
            </Box>

            <List sx={{ flexGrow: 1, overflowY: 'auto', p: 0 }}>
                <AnimatePresence initial={false}>
                    {history.length === 0 ? (
                        <Box sx={{ p: 4, textAlign: 'center', opacity: 0.5 }}>
                            <HistoryIcon sx={{ fontSize: 48, mb: 2, opacity: 0.5 }} />
                            <Typography variant="body2">No analysis history yet</Typography>
                        </Box>
                    ) : (
                        history.map((item) => (
                            <ListItem
                                key={item.id}
                                component={motion.li}
                                layout
                                initial={{ opacity: 0, x: -20 }}
                                animate={{ opacity: 1, x: 0 }}
                                exit={{ opacity: 0, x: 20 }}
                                sx={{
                                    borderBottom: '1px solid rgba(255,255,255,0.05)',
                                    '&:hover': { bgcolor: 'rgba(255,255,255,0.02)' },
                                    pr: 1
                                }}
                                secondaryAction={
                                    <Stack direction="row" spacing={0.5}>
                                        <Tooltip title="Restore">
                                            <IconButton edge="end" size="small" onClick={() => onRestore(item)} sx={{ color: 'primary.main' }}>
                                                <Restore fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                        <Tooltip title="Delete">
                                            <IconButton edge="end" size="small" onClick={() => onDelete(item.id)} sx={{ color: 'error.main' }}>
                                                <Delete fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                    </Stack>
                                }
                            >
                                <ListItemText
                                    primary={
                                        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
                                            <Chip
                                                label={item.language}
                                                size="small"
                                                sx={{ height: 20, fontSize: '0.7rem', textTransform: 'capitalize' }}
                                            />
                                            <Typography variant="body2" fontWeight={600}>
                                                Score: <span style={{ color: item.summary.security_score >= 90 ? '#4ade80' : item.summary.security_score >= 70 ? '#facc15' : '#f87171' }}>
                                                    {item.summary.security_score}
                                                </span>
                                            </Typography>
                                        </Stack>
                                    }
                                    secondary={
                                        <Stack direction="row" alignItems="center" spacing={0.5} sx={{ opacity: 0.7 }}>
                                            <AccessTime sx={{ fontSize: 12 }} />
                                            <Typography variant="caption">{formatDate(item.timestamp)}</Typography>
                                            <Typography variant="caption">• {item.summary.total_issues} issues</Typography>
                                        </Stack>
                                    }
                                />
                            </ListItem>
                        ))
                    )}
                </AnimatePresence>
            </List>
        </Paper>
    );
};

export default HistoryPanel;
