import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  LinearProgress,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Chip,
  Divider,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import {
  Security,
  PlayArrow,
  Stop,
  Refresh,
  Warning,
  Error,
  CheckCircle,
  Info,
  BugReport,
  Shield,
  VpnLock,
  Code,
  Visibility,
  GetApp,
} from '@mui/icons-material';

interface SecurityIssue {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: string;
  title: string;
  description: string;
  file: string;
  line: number;
  cwe?: string;
  cvss?: number;
  recommendation: string;
  impact: string;
}

const mockSecurityIssues: SecurityIssue[] = [
  {
    id: '1',
    severity: 'critical',
    category: 'Injection',
    title: 'SQL Injection Vulnerability',
    description: 'User input is directly concatenated into SQL query without sanitization',
    file: 'src/auth/login.js',
    line: 45,
    cwe: 'CWE-89',
    cvss: 9.8,
    recommendation: 'Use parameterized queries or prepared statements',
    impact: 'Attackers could execute arbitrary SQL commands and access sensitive data',
  },
  {
    id: '2',
    severity: 'high',
    category: 'Authentication',
    title: 'Weak Password Policy',
    description: 'Password requirements are insufficient for security',
    file: 'src/auth/validation.js',
    line: 23,
    cwe: 'CWE-521',
    cvss: 7.5,
    recommendation: 'Implement stronger password requirements (minimum 12 characters, complexity)',
    impact: 'Weak passwords can be easily compromised through brute force attacks',
  },
  {
    id: '3',
    severity: 'high',
    category: 'Cryptography',
    title: 'Hardcoded Encryption Key',
    description: 'Encryption key is hardcoded in source code',
    file: 'src/utils/crypto.js',
    line: 12,
    cwe: 'CWE-798',
    cvss: 8.1,
    recommendation: 'Store encryption keys in environment variables or secure key management system',
    impact: 'Hardcoded keys can be extracted from source code, compromising all encrypted data',
  },
  {
    id: '4',
    severity: 'medium',
    category: 'Input Validation',
    title: 'Cross-Site Scripting (XSS)',
    description: 'User input is rendered without proper sanitization',
    file: 'src/components/UserProfile.js',
    line: 67,
    cwe: 'CWE-79',
    cvss: 6.1,
    recommendation: 'Sanitize user input and use Content Security Policy headers',
    impact: 'Attackers could execute malicious scripts in user browsers',
  },
  {
    id: '5',
    severity: 'medium',
    category: 'Session Management',
    title: 'Insecure Session Configuration',
    description: 'Session cookies lack secure flags',
    file: 'src/middleware/session.js',
    line: 34,
    cwe: 'CWE-614',
    cvss: 5.4,
    recommendation: 'Set HttpOnly, Secure, and SameSite flags on session cookies',
    impact: 'Session cookies could be intercepted or accessed by malicious scripts',
  },
];

const SecurityScan: React.FC = () => {
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);
  const [scanResults, setScanResults] = useState<SecurityIssue[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [selectedIssue, setSelectedIssue] = useState<SecurityIssue | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);

  const handleStartScan = () => {
    setIsScanning(true);
    setScanProgress(0);
    setShowResults(false);
    
    // Simulate scanning progress
    const interval = setInterval(() => {
      setScanProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsScanning(false);
          setScanResults(mockSecurityIssues);
          setShowResults(true);
          return 100;
        }
        return prev + 10;
      });
    }, 300);
  };

  const handleStopScan = () => {
    setIsScanning(false);
    setScanProgress(0);
  };

  const handleIssueClick = (issue: SecurityIssue) => {
    setSelectedIssue(issue);
    setDetailDialogOpen(true);
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return '#d32f2f';
      case 'high':
        return '#f57c00';
      case 'medium':
        return '#fbc02d';
      case 'low':
        return '#388e3c';
      default:
        return '#757575';
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <Error sx={{ color: getSeverityColor(severity) }} />;
      case 'high':
        return <Warning sx={{ color: getSeverityColor(severity) }} />;
      case 'medium':
        return <Info sx={{ color: getSeverityColor(severity) }} />;
      case 'low':
        return <CheckCircle sx={{ color: getSeverityColor(severity) }} />;
      default:
        return <Info />;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category.toLowerCase()) {
      case 'injection':
        return <BugReport />;
      case 'authentication':
        return <VpnLock />;
      case 'cryptography':
        return <Shield />;
      default:
        return <Security />;
    }
  };

  const severityCounts = scanResults.reduce((acc, issue) => {
    acc[issue.severity] = (acc[issue.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
          Security Vulnerability Scanner
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Comprehensive security analysis based on OWASP Top 10 and industry best practices
        </Typography>
      </Box>

      {/* Scan Control */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" component="h2" sx={{ fontWeight: 600 }}>
              Security Scan
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              {!isScanning ? (
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={handleStartScan}
                  size="large"
                >
                  Start Security Scan
                </Button>
              ) : (
                <Button
                  variant="outlined"
                  startIcon={<Stop />}
                  onClick={handleStopScan}
                  color="error"
                >
                  Stop Scan
                </Button>
              )}
              <Tooltip title="Refresh">
                <IconButton onClick={() => window.location.reload()}>
                  <Refresh />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
          
          {isScanning && (
            <Box sx={{ mt: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Scanning for vulnerabilities...</Typography>
                <Typography variant="body2">{scanProgress}%</Typography>
              </Box>
              <LinearProgress variant="determinate" value={scanProgress} />
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Scan Results Summary */}
      {showResults && (
        <Grid container spacing={3} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ textAlign: 'center', bgcolor: '#ffebee' }}>
              <CardContent>
                <Typography variant="h4" sx={{ color: '#d32f2f', fontWeight: 700 }}>
                  {severityCounts.critical || 0}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Critical Issues
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ textAlign: 'center', bgcolor: '#fff3e0' }}>
              <CardContent>
                <Typography variant="h4" sx={{ color: '#f57c00', fontWeight: 700 }}>
                  {severityCounts.high || 0}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  High Risk
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ textAlign: 'center', bgcolor: '#fffde7' }}>
              <CardContent>
                <Typography variant="h4" sx={{ color: '#fbc02d', fontWeight: 700 }}>
                  {severityCounts.medium || 0}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Medium Risk
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card sx={{ textAlign: 'center', bgcolor: '#e8f5e8' }}>
              <CardContent>
                <Typography variant="h4" sx={{ color: '#388e3c', fontWeight: 700 }}>
                  {severityCounts.low || 0}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Low Risk
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      )}

      {/* Security Issues List */}
      {showResults && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6" component="h2" sx={{ fontWeight: 600 }}>
                Security Issues ({scanResults.length} found)
              </Typography>
              <Button startIcon={<GetApp />} variant="outlined" size="small">
                Export Report
              </Button>
            </Box>

            {scanResults.length === 0 ? (
              <Alert severity="success" sx={{ mt: 2 }}>
                <Typography variant="body1">
                  🎉 No security vulnerabilities found! Your code appears to be secure.
                </Typography>
              </Alert>
            ) : (
              <TableContainer component={Paper} variant="outlined">
                <Table>
                  <TableHead>
                    <TableRow>
                      <TableCell>Severity</TableCell>
                      <TableCell>Category</TableCell>
                      <TableCell>Issue</TableCell>
                      <TableCell>File</TableCell>
                      <TableCell>CVSS</TableCell>
                      <TableCell>Actions</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {scanResults.map((issue) => (
                      <TableRow
                        key={issue.id}
                        hover
                        sx={{ cursor: 'pointer' }}
                        onClick={() => handleIssueClick(issue)}
                      >
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {getSeverityIcon(issue.severity)}
                            <Chip
                              label={issue.severity.toUpperCase()}
                              size="small"
                              sx={{
                                backgroundColor: getSeverityColor(issue.severity),
                                color: 'white',
                                fontWeight: 600,
                              }}
                            />
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            {getCategoryIcon(issue.category)}
                            <Typography variant="body2">{issue.category}</Typography>
                          </Box>
                        </TableCell>
                        <TableCell>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                            {issue.title}
                          </Typography>
                          <Typography variant="body2" color="textSecondary" noWrap>
                            {issue.description}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                            {issue.file}:{issue.line}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" sx={{ fontWeight: 600 }}>
                            {issue.cvss || 'N/A'}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Tooltip title="View Details">
                            <IconButton size="small">
                              <Visibility />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </CardContent>
        </Card>
      )}

      {/* Issue Detail Dialog */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        {selectedIssue && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {getSeverityIcon(selectedIssue.severity)}
                <Box>
                  <Typography variant="h6">{selectedIssue.title}</Typography>
                  <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                    <Chip
                      label={selectedIssue.severity.toUpperCase()}
                      size="small"
                      sx={{
                        backgroundColor: getSeverityColor(selectedIssue.severity),
                        color: 'white',
                      }}
                    />
                    <Chip label={selectedIssue.category} size="small" variant="outlined" />
                    {selectedIssue.cwe && (
                      <Chip label={selectedIssue.cwe} size="small" variant="outlined" />
                    )}
                  </Box>
                </Box>
              </Box>
            </DialogTitle>
            <DialogContent>
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                  Description
                </Typography>
                <Typography variant="body2" paragraph>
                  {selectedIssue.description}
                </Typography>
              </Box>
              
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                  Location
                </Typography>
                <Typography variant="body2" sx={{ fontFamily: 'monospace', bgcolor: 'grey.100', p: 1, borderRadius: 1 }}>
                  {selectedIssue.file}:{selectedIssue.line}
                </Typography>
              </Box>
              
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                  Impact
                </Typography>
                <Typography variant="body2" paragraph>
                  {selectedIssue.impact}
                </Typography>
              </Box>
              
              <Alert severity="info">
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  Recommendation
                </Typography>
                <Typography variant="body2">
                  {selectedIssue.recommendation}
                </Typography>
              </Alert>
              
              {selectedIssue.cvss && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                    CVSS Score: {selectedIssue.cvss}/10
                  </Typography>
                  <LinearProgress
                    variant="determinate"
                    value={(selectedIssue.cvss / 10) * 100}
                    sx={{
                      height: 8,
                      borderRadius: 4,
                      backgroundColor: 'grey.200',
                      '& .MuiLinearProgress-bar': {
                        backgroundColor: getSeverityColor(selectedIssue.severity),
                      },
                    }}
                  />
                </Box>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
              <Button variant="contained">Fix Issue</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default SecurityScan;