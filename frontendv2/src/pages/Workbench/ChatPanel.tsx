import React, { useState, useRef, useEffect } from 'react';
import { Box, Paper, Typography, TextField, IconButton, List, ListItem, CircularProgress, Avatar } from '@mui/material';
import { Send, SmartToy, Person } from '@mui/icons-material';
import type { ChatMessage } from '../../types';
import ReactMarkdown from 'react-markdown';

interface ChatPanelProps {
    messages: ChatMessage[];
    onSendMessage: (message: string) => void;
    isLoading: boolean;
}

const ChatPanel: React.FC<ChatPanelProps> = ({ messages, onSendMessage, isLoading }) => {
    const [input, setInput] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = () => {
        if (input.trim() && !isLoading) {
            onSendMessage(input);
            setInput('');
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <Paper
            className="glass-panel"
            sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                borderRadius: 3,
                overflow: 'hidden'
            }}
        >
            <Box sx={{ p: 2, borderBottom: '1px solid rgba(255,255,255,0.1)' }}>
                <Typography variant="h6" sx={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: 1 }}>
                    <SmartToy color="primary" />
                    AI Assistant
                </Typography>
            </Box>

            <List sx={{ flexGrow: 1, overflow: 'auto', p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
                {messages.length === 0 && (
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', opacity: 0.6, gap: 1 }}>
                        <SmartToy sx={{ fontSize: 48 }} />
                        <Typography variant="body1">Ask me anything about your code!</Typography>
                    </Box>
                )}

                {messages.map((msg) => (
                    <ListItem
                        key={msg.id}
                        sx={{
                            flexDirection: 'column',
                            alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                            p: 0
                        }}
                    >
                        <Box sx={{
                            display: 'flex',
                            gap: 1,
                            flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                            maxWidth: '85%'
                        }}>
                            <Avatar
                                sx={{
                                    width: 32,
                                    height: 32,
                                    bgcolor: msg.role === 'user' ? 'secondary.main' : 'primary.main'
                                }}
                            >
                                {msg.role === 'user' ? <Person fontSize="small" /> : <SmartToy fontSize="small" />}
                            </Avatar>
                            <Paper
                                elevation={0}
                                sx={{
                                    p: 1.5,
                                    borderRadius: 2,
                                    bgcolor: msg.role === 'user' ? 'secondary.dark' : 'action.hover',
                                    color: 'text.primary',
                                    '& pre': {
                                        m: 0,
                                        p: 1,
                                        borderRadius: 1,
                                        bgcolor: 'background.paper',
                                        overflow: 'auto',
                                        fontSize: '0.875rem',
                                    },
                                    '& code': {
                                        fontFamily: 'monospace',
                                    }
                                }}
                            >
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                            </Paper>
                        </Box>
                    </ListItem>
                ))}
                {isLoading && (
                    <ListItem sx={{ p: 0 }}>
                        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
                                <SmartToy fontSize="small" />
                            </Avatar>
                            <Box sx={{ p: 1.5, borderRadius: 2, bgcolor: 'action.hover' }}>
                                <CircularProgress size={20} />
                            </Box>
                        </Box>
                    </ListItem>
                )}
                <div ref={messagesEndRef} />
            </List>

            <Box sx={{ p: 2, borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', gap: 1 }}>
                <TextField
                    fullWidth
                    size="small"
                    placeholder="Type your message..."
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    disabled={isLoading}
                    sx={{
                        '& .MuiOutlinedInput-root': {
                            borderRadius: 2
                        }
                    }}
                />
                <IconButton
                    color="primary"
                    onClick={handleSend}
                    disabled={!input.trim() || isLoading}
                    sx={{
                        bgcolor: 'primary.main',
                        color: 'white',
                        '&:hover': { bgcolor: 'primary.dark' },
                        '&:disabled': { bgcolor: 'action.disabledBackground' }
                    }}
                >
                    <Send />
                </IconButton>
            </Box>
        </Paper>
    );
};

export default ChatPanel;
