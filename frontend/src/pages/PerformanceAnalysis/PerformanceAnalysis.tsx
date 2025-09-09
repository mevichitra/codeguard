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
  Chip,
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
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  Speed,
  PlayArrow,
  Stop,
  Refresh,
  TrendingUp,
  TrendingDown,
  Memory,
  Timer,
  Code,
  Visibility,
  GetApp,
  Warning,
  CheckCircle,
  Error,
  Functions,
  AccountTree,
  Storage,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';

interface PerformanceIssue {
  id: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  category: 'complexity' | 'memory' | 'runtime' | 'algorithm';
  title: string;
  description: string;
  file: string;
  function: string;
  line: number;
  metric: string;
  value: number;
  threshold: number;
  recommendation: string;
  impact: string;
}

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <div hidden={value !== index}>
      {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
    </div>
  );
};

const mockPerformanceData = {
  complexityTrend: [
    { name: 'Jan', complexity: 12, maintainability: 85 },
    { name: 'Feb', complexity: 15, maintainability: 82 },
    { name: 'Mar', complexity: 18, maintainability: 78 },
    { name: 'Apr', complexity: 14, maintainability: 83 },
    { name: 'May', complexity: 16, maintainability: 80 },
    { name: 'Jun', complexity: 13, maintainability: 86 },
  ],
  performanceMetrics: [
    { name: 'CPU Usage', value: 65, color: '#8884d8' },
    { name: 'Memory Usage', value: 45, color: '#82ca9d' },
    { name: 'I/O Operations', value: 30, color: '#ffc658' },
    { name: 'Network Calls', value: 25, color: '#ff7300' },
  ],
  codeQuality: [
    { subject: 'Maintainability', A: 85, B: 90, fullMark: 100 },
    { subject: 'Reliability', A: 78, B: 85, fullMark: 100 },
    { subject: 'Security', A: 92, B: 95, fullMark: 100 },
    { subject: 'Performance', A: 73, B: 80, fullMark: 100 },
    { subject: 'Testability', A: 68, B: 75, fullMark: 100 },
    { subject: 'Reusability', A: 81, B: 88, fullMark: 100 },
  ],
};

const mockPerformanceIssues: PerformanceIssue[] = [
  {
    id: '1',
    severity: 'critical',
    category: 'complexity',
    title: 'High Cyclomatic Complexity',
    description: 'Function has excessive branching logic making it hard to maintain',
    file: 'src/utils/dataProcessor.js',
    function: 'processUserData',
    line: 45,
    metric: 'Cyclomatic Complexity',
    value: 25,
    threshold: 10,
    recommendation: 'Break down function into smaller, more focused functions',
    impact: 'Increased maintenance cost and higher bug probability',
  },
  {
    id: '2',
    severity: 'high',
    category: 'memory',
    title: 'Memory Leak Potential',
    description: 'Event listeners not properly cleaned up in component',
    file: 'src/components/DataVisualization.js',
    function: 'useEffect',
    line: 78,
    metric: 'Memory Usage',
    value: 150,
    threshold: 100,
    recommendation: 'Add cleanup function in useEffect return statement',
    impact: 'Progressive memory consumption leading to performance degradation',
  },
  {
    id: '3',
    severity: 'high',
    category: 'runtime',
    title: 'Inefficient Loop Operation',
    description: 'Nested loops with O(n²) complexity processing large datasets',
    file: 'src/services/analyticsService.js',
    function: 'calculateMetrics',
    line: 123,
    metric: 'Time Complexity',
    value: 2,
    threshold: 1,
    recommendation: 'Use hash maps or optimize algorithm to reduce complexity',
    impact: 'Exponential performance degradation with larger datasets',
  },
  {
    id: '4',
    severity: 'medium',
    category: 'algorithm',
    title: 'Suboptimal Sorting Algorithm',
    description: 'Using bubble sort for large array operations',
    file: 'src/utils/arrayHelpers.js',
    function: 'sortResults',
    line: 34,
    metric: 'Algorithm Efficiency',
    value: 3,
    threshold: 2,
    recommendation: 'Replace with quicksort or use native Array.sort()',
    impact: 'Slower response times for data sorting operations',
  },
  {
    id: '5',
    severity: 'medium',
    category: 'memory',
    title: 'Large Object Creation',
    description: 'Creating large objects in render loop causing GC pressure',
    file: 'src/components/Dashboard.js',
    function: 'render',
    line: 156,
    metric: 'Object Size',
    value: 500,
    threshold: 200,
    recommendation: 'Move object creation outside render or use useMemo',
    impact: 'Frequent garbage collection causing UI stuttering',
  },
];

const PerformanceAnalysis: React.FC = () => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisProgress, setAnalysisProgress] = useState(0);
  const [analysisResults, setAnalysisResults] = useState<PerformanceIssue[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [selectedIssue, setSelectedIssue] = useState<PerformanceIssue | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [tabValue, setTabValue] = useState(0);

  const handleStartAnalysis = () => {
    setIsAnalyzing(true);
    setAnalysisProgress(0);
    setShowResults(false);
    
    // Simulate analysis progress
    const interval = setInterval(() => {
      setAnalysisProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setIsAnalyzing(false);
          setAnalysisResults(mockPerformanceIssues);
          setShowResults(true);
          return 100;
        }
        return prev + 8;
      });
    }, 400);
  };

  const handleStopAnalysis = () => {
    setIsAnalyzing(false);
    setAnalysisProgress(0);
  };

  const handleIssueClick = (issue: PerformanceIssue) => {
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
        return <TrendingDown sx={{ color: getSeverityColor(severity) }} />;
      case 'low':
        return <CheckCircle sx={{ color: getSeverityColor(severity) }} />;
      default:
        return <Speed />;
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'complexity':
        return <AccountTree />;
      case 'memory':
        return <Memory />;
      case 'runtime':
        return <Timer />;
      case 'algorithm':
        return <Functions />;
      default:
        return <Speed />;
    }
  };

  const severityCounts = analysisResults.reduce((acc, issue) => {
    acc[issue.severity] = (acc[issue.severity] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const categoryStats = analysisResults.reduce((acc, issue) => {
    acc[issue.category] = (acc[issue.category] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
          Performance Analysis
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Comprehensive code performance analysis including complexity, memory usage, and optimization opportunities
        </Typography>
      </Box>

      {/* Analysis Control */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" component="h2" sx={{ fontWeight: 600 }}>
              Performance Analysis
            </Typography>
            <Box sx={{ display: 'flex', gap: 1 }}>
              {!isAnalyzing ? (
                <Button
                  variant="contained"
                  startIcon={<PlayArrow />}
                  onClick={handleStartAnalysis}
                  size="large"
                >
                  Start Analysis
                </Button>
              ) : (
                <Button
                  variant="outlined"
                  startIcon={<Stop />}
                  onClick={handleStopAnalysis}
                  color="error"
                >
                  Stop Analysis
                </Button>
              )}
              <Tooltip title="Refresh">
                <IconButton onClick={() => window.location.reload()}>
                  <Refresh />
                </IconButton>
              </Tooltip>
            </Box>
          </Box>
          
          {isAnalyzing && (
            <Box sx={{ mt: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="body2">Analyzing code performance...</Typography>
                <Typography variant="body2">{analysisProgress}%</Typography>
              </Box>
              <LinearProgress variant="determinate" value={analysisProgress} />
            </Box>
          )}
        </CardContent>
      </Card>

      {/* Results Tabs */}
      {showResults && (
        <Card>
          <CardContent>
            <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
              <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
                <Tab label="Overview" />
                <Tab label="Performance Issues" />
                <Tab label="Metrics & Trends" />
                <Tab label="Code Quality" />
              </Tabs>
            </Box>

            {/* Overview Tab */}
            <TabPanel value={tabValue} index={0}>
              <Grid container spacing={3}>
                {/* Severity Summary */}
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                    Issues by Severity
                  </Typography>
                  <Grid container spacing={2}>
                    <Grid item xs={6}>
                      <Card sx={{ textAlign: 'center', bgcolor: '#ffebee' }}>
                        <CardContent sx={{ py: 2 }}>
                          <Typography variant="h4" sx={{ color: '#d32f2f', fontWeight: 700 }}>
                            {severityCounts.critical || 0}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            Critical
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={6}>
                      <Card sx={{ textAlign: 'center', bgcolor: '#fff3e0' }}>
                        <CardContent sx={{ py: 2 }}>
                          <Typography variant="h4" sx={{ color: '#f57c00', fontWeight: 700 }}>
                            {severityCounts.high || 0}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            High
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={6}>
                      <Card sx={{ textAlign: 'center', bgcolor: '#fffde7' }}>
                        <CardContent sx={{ py: 2 }}>
                          <Typography variant="h4" sx={{ color: '#fbc02d', fontWeight: 700 }}>
                            {severityCounts.medium || 0}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            Medium
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid item xs={6}>
                      <Card sx={{ textAlign: 'center', bgcolor: '#e8f5e8' }}>
                        <CardContent sx={{ py: 2 }}>
                          <Typography variant="h4" sx={{ color: '#388e3c', fontWeight: 700 }}>
                            {severityCounts.low || 0}
                          </Typography>
                          <Typography variant="body2" color="textSecondary">
                            Low
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                </Grid>

                {/* Category Breakdown */}
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                    Issues by Category
                  </Typography>
                  <List>
                    {Object.entries(categoryStats).map(([category, count]) => (
                      <ListItem key={category}>
                        <ListItemIcon>
                          {getCategoryIcon(category)}
                        </ListItemIcon>
                        <ListItemText
                          primary={category.charAt(0).toUpperCase() + category.slice(1)}
                          secondary={`${count} issues found`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Grid>
              </Grid>
            </TabPanel>

            {/* Performance Issues Tab */}
            <TabPanel value={tabValue} index={1}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
                <Typography variant="h6" component="h2" sx={{ fontWeight: 600 }}>
                  Performance Issues ({analysisResults.length} found)
                </Typography>
                <Button startIcon={<GetApp />} variant="outlined" size="small">
                  Export Report
                </Button>
              </Box>

              {analysisResults.length === 0 ? (
                <Alert severity="success">
                  <Typography variant="body1">
                    🎉 No performance issues found! Your code is well optimized.
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
                        <TableCell>Metric</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {analysisResults.map((issue) => (
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
                            <Typography variant="caption" color="textSecondary">
                              {issue.function}()
                            </Typography>
                          </TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ fontWeight: 600 }}>
                              {issue.metric}: {issue.value}
                            </Typography>
                            <Typography variant="caption" color="textSecondary">
                              Threshold: {issue.threshold}
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
            </TabPanel>

            {/* Metrics & Trends Tab */}
            <TabPanel value={tabValue} index={2}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                    Complexity Trend
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={mockPerformanceData.complexityTrend}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <RechartsTooltip />
                      <Line type="monotone" dataKey="complexity" stroke="#8884d8" strokeWidth={2} />
                      <Line type="monotone" dataKey="maintainability" stroke="#82ca9d" strokeWidth={2} />
                    </LineChart>
                  </ResponsiveContainer>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                    Performance Metrics
                  </Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={mockPerformanceData.performanceMetrics}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis />
                      <RechartsTooltip />
                      <Bar dataKey="value" fill="#8884d8" />
                    </BarChart>
                  </ResponsiveContainer>
                </Grid>
              </Grid>
            </TabPanel>

            {/* Code Quality Tab */}
            <TabPanel value={tabValue} index={3}>
              <Grid container spacing={3}>
                <Grid item xs={12} md={8}>
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                    Code Quality Radar
                  </Typography>
                  <ResponsiveContainer width="100%" height={400}>
                    <RadarChart data={mockPerformanceData.codeQuality}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="subject" />
                      <PolarRadiusAxis angle={90} domain={[0, 100]} />
                      <Radar name="Current" dataKey="A" stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
                      <Radar name="Target" dataKey="B" stroke="#82ca9d" fill="#82ca9d" fillOpacity={0.6} />
                      <RechartsTooltip />
                    </RadarChart>
                  </ResponsiveContainer>
                </Grid>
                <Grid item xs={12} md={4}>
                  <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                    Quality Metrics
                  </Typography>
                  <List>
                    {mockPerformanceData.codeQuality.map((metric) => (
                      <ListItem key={metric.subject}>
                        <ListItemText
                          primary={metric.subject}
                          secondary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                              <LinearProgress
                                variant="determinate"
                                value={metric.A}
                                sx={{ flexGrow: 1, height: 8, borderRadius: 4 }}
                              />
                              <Typography variant="body2" sx={{ minWidth: 40 }}>
                                {metric.A}%
                              </Typography>
                            </Box>
                          }
                        />
                      </ListItem>
                    ))}
                  </List>
                </Grid>
              </Grid>
            </TabPanel>
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
                  {selectedIssue.file}:{selectedIssue.line} in {selectedIssue.function}()
                </Typography>
              </Box>
              
              <Box sx={{ mb: 3 }}>
                <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                  Performance Metric
                </Typography>
                <Typography variant="body2">
                  {selectedIssue.metric}: <strong>{selectedIssue.value}</strong> (threshold: {selectedIssue.threshold})
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
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
              <Button variant="contained">Optimize Code</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default PerformanceAnalysis;