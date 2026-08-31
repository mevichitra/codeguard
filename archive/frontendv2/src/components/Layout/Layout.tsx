import React from 'react';
import { Box, Drawer, List, ListItem, ListItemButton, ListItemIcon, ListItemText, Typography, Avatar, Divider } from '@mui/material';
import { Code, History, Settings, Logout } from '@mui/icons-material';
import { useLocation, useNavigate } from 'react-router-dom';

const drawerWidth = 240;

interface LayoutProps {
    children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
    const navigate = useNavigate();
    const location = useLocation();

    const menuItems = [
        { text: 'Workbench', icon: <Code />, path: '/workbench' },
        { text: 'History', icon: <History />, path: '/history' },
    ];

    return (
        <Box sx={{ display: 'flex', height: '100vh' }}>
            <Drawer
                variant="permanent"
                sx={{
                    width: drawerWidth,
                    flexShrink: 0,
                    [`& .MuiDrawer-paper`]: {
                        width: drawerWidth,
                        boxSizing: 'border-box',
                        bgcolor: 'rgba(15, 23, 42, 0.6)',
                        backdropFilter: 'blur(12px)',
                        borderRight: '1px solid rgba(255,255,255,0.08)',
                        color: 'text.primary'
                    },
                }}
            >
                <Box sx={{ p: 3, display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <Box
                        sx={{
                            width: 32,
                            height: 32,
                            borderRadius: 1,
                            background: 'linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center'
                        }}
                    >
                        <Code sx={{ color: 'white', fontSize: 20 }} />
                    </Box>
                    <Typography variant="h6" sx={{ fontWeight: 700, letterSpacing: '-0.02em' }}>
                        CodeGuard
                    </Typography>
                </Box>

                <List sx={{ px: 2, mt: 2 }}>
                    {menuItems.map((item) => (
                        <ListItem key={item.text} disablePadding sx={{ mb: 1 }}>
                            <ListItemButton
                                selected={location.pathname === item.path}
                                onClick={() => navigate(item.path)}
                                sx={{
                                    borderRadius: 2,
                                    '&.Mui-selected': {
                                        bgcolor: 'rgba(99, 102, 241, 0.15)',
                                        color: 'primary.main',
                                        '&:hover': {
                                            bgcolor: 'rgba(99, 102, 241, 0.25)',
                                        },
                                        '& .MuiListItemIcon-root': {
                                            color: 'primary.main',
                                        },
                                    },
                                    '&:hover': {
                                        bgcolor: 'rgba(255, 255, 255, 0.05)',
                                    },
                                }}
                            >
                                <ListItemIcon sx={{ minWidth: 40, color: 'text.secondary' }}>
                                    {item.icon}
                                </ListItemIcon>
                                <ListItemText
                                    primary={item.text}
                                    primaryTypographyProps={{ fontWeight: 500, fontSize: '0.95rem' }}
                                />
                            </ListItemButton>
                        </ListItem>
                    ))}
                </List>

                <Box sx={{ mt: 'auto', p: 2 }}>
                    <Box
                        className="glass-card"
                        sx={{
                            p: 2,
                            borderRadius: 3,
                            display: 'flex',
                            alignItems: 'center',
                            gap: 1.5,
                            cursor: 'pointer',
                            '&:hover': { bgcolor: 'rgba(255,255,255,0.05)' }
                        }}
                    >
                        <Avatar sx={{ width: 32, height: 32, bgcolor: 'secondary.main' }}>V</Avatar>
                        <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
                            <Typography variant="subtitle2" noWrap>Vichitra</Typography>
                            <Typography variant="caption" color="text.secondary" noWrap>Pro Plan</Typography>
                        </Box>
                        <Settings fontSize="small" sx={{ color: 'text.secondary' }} />
                    </Box>
                </Box>
            </Drawer>

            <Box component="main" sx={{ flexGrow: 1, p: 3, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                {children}
            </Box>
        </Box>
    );
};

export default Layout;
