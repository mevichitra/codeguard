import React, { useState } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
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
  TextField,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Avatar,
  Divider,
} from '@mui/material';
import {
  Assessment,
  GetApp,
  Visibility,
  Share,
  Schedule,
  FilterList,
  Search,
  PictureAsPdf,
  TableChart,
  InsertChart,
  Security,
  Speed,
  Code,
  BugReport,
  CheckCircle,
  Warning,
  Error,
  Refresh,
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
} from 'recharts';

interface Report {
  id: string;
  title: string;
  type: 'security' | 'performance' | 'quality' | 'ai-detection';
  status: 'completed' | 'in-progress' | 'failed';
  createdAt: string;
  createdBy: string;
  description: string;
  filesScanned: number;
  issuesFound: number;
  severity: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  duration: string;
  size: string;
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

const mockReports: Report[] = [
  {
    id: '1',
    title: 'Weekly Security Scan - Frontend',
    type: 'security',
    status: 'completed',
    createdAt: '2024-01-15T10:30:00Z',
    createdBy: 'John Doe',
    description: 'Comprehensive security analysis of frontend codebase',
    filesScanned: 156,
    issuesFound: 8,
    severity: { critical: 2, high: 3, medium: 2, low: 1 },
    duration: '12m 34s',
    size: '2.4 MB',
  },
  {
    id: '2',
    title: 'Performance Analysis - API Services',
    type: 'performance',
    status: 'completed',
    createdAt: '2024-01-14T15:45:00Z',
    createdBy: 'Jane Smith',
    description: 'Performance bottleneck analysis for API endpoints',
    filesScanned: 89,
    issuesFound: 12,
    severity: { critical: 1, high: 4, medium: 5, low: 2 },
    duration: '8m 21s',
    size: '1.8 MB',
  },
  {
    id: '3',
    title: 'AI Code Detection - Full Repository',
    type: 'ai-detection',
    status: 'completed',
    createdAt: '2024-01-13T09:15:00Z',
    createdBy: 'Mike Johnson',
    description: 'AI-generated code detection across entire repository',
    filesScanned: 234,
    issuesFound: 5,
    severity: { critical: 0, high: 1, medium: 3, low: 1 },
    duration: '15m 42s',
    size: '3.1 MB',
  },
  {
    id: '4',
    title: 'Code Quality Assessment',
    type: 'quality',
    status: 'in-progress',
    createdAt: '2024-01-15T14:20:00Z',
    createdBy: 'Sarah Wilson',
    description: 'Comprehensive code quality and maintainability analysis',
    filesScanned: 178,
    issuesFound: 0,
    severity: { critical: 0, high: 0, medium: 0, low: 0 },
    duration: '5m 12s',
    size: '0.9 MB',
  },
  {
    id: '5',
    title: 'Security Audit - Authentication Module',
    type: 'security',
    status: 'failed',
    createdAt: '2024-01-12T11:30:00Z',
    createdBy: 'David Brown',
    description: 'Focused security audit of authentication and authorization',
    filesScanned: 45,
    issuesFound: 0,
    severity: { critical: 0, high: 0, medium: 0, low: 0 },
    duration: '2m 15s',
    size: '0.3 MB',
  },
];

const mockTrendData = [
  { name: 'Jan', security: 12, performance: 8, quality: 15, ai: 3 },
  { name: 'Feb', security: 15, performance: 12, quality: 18, ai: 5 },
  { name: 'Mar', security: 8, performance: 15, quality: 12, ai: 2 },
  { name: 'Apr', security: 10, performance: 9, quality: 20, ai: 4 },
  { name: 'May', security: 6, performance: 11, quality: 16, ai: 6 },
  { name: 'Jun', security: 9, performance: 7, quality: 14, ai: 3 },
];

const Reports: React.FC = () => {
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [detailDialogOpen, setDetailDialogOpen] = useState(false);
  const [tabValue, setTabValue] = useState(0);
  const [filterType, setFilterType] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');

  const handleReportClick = (report: Report) => {
    setSelectedReport(report);
    setDetailDialogOpen(true);
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'security':
        return <Security />;
      case 'performance':
        return <Speed />;
      case 'quality':
        return <Code />;
      case 'ai-detection':
        return <BugReport />;
      default:
        return <Assessment />;
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'security':
        return '#d32f2f';
      case 'performance':
        return '#1976d2';
      case 'quality':
        return '#388e3c';
      case 'ai-detection':
        return '#f57c00';
      default:
        return '#757575';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle sx={{ color: '#388e3c' }} />;
      case 'in-progress':
        return <Schedule sx={{ color: '#1976d2' }} />;
      case 'failed':
        return <Error sx={{ color: '#d32f2f' }} />;
      default:
        return <Warning />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return '#388e3c';
      case 'in-progress':
        return '#1976d2';
      case 'failed':
        return '#d32f2f';
      default:
        return '#757575';
    }
  };

  const filteredReports = mockReports.filter(report => {
    const matchesType = filterType === 'all' || report.type === filterType;
    const matchesStatus = filterStatus === 'all' || report.status === filterStatus;
    const matchesSearch = report.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         report.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesStatus && matchesSearch;
  });

  const reportStats = {
    total: mockReports.length,
    completed: mockReports.filter(r => r.status === 'completed').length,
    inProgress: mockReports.filter(r => r.status === 'in-progress').length,
    failed: mockReports.filter(r => r.status === 'failed').length,
  };

  const typeDistribution = mockReports.reduce((acc, report) => {
    acc[report.type] = (acc[report.type] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const pieData = Object.entries(typeDistribution).map(([type, count]) => ({
    name: type,
    value: count,
    color: getTypeColor(type),
  }));

  return (
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
          Analysis Reports
        </Typography>
        <Typography variant="body1" color="textSecondary">
          View, manage, and analyze your code analysis reports and trends
        </Typography>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ textAlign: 'center' }}>
            <CardContent>
              <Typography variant="h4" sx={{ color: '#1976d2', fontWeight: 700 }}>
                {reportStats.total}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Total Reports
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ textAlign: 'center', bgcolor: '#e8f5e8' }}>
            <CardContent>
              <Typography variant="h4" sx={{ color: '#388e3c', fontWeight: 700 }}>
                {reportStats.completed}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Completed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ textAlign: 'center', bgcolor: '#e3f2fd' }}>
            <CardContent>
              <Typography variant="h4" sx={{ color: '#1976d2', fontWeight: 700 }}>
                {reportStats.inProgress}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                In Progress
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card sx={{ textAlign: 'center', bgcolor: '#ffebee' }}>
            <CardContent>
              <Typography variant="h4" sx={{ color: '#d32f2f', fontWeight: 700 }}>
                {reportStats.failed}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Failed
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Main Content */}
      <Card>
        <CardContent>
          <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
            <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
              <Tab label="All Reports" />
              <Tab label="Analytics" />
              <Tab label="Scheduled Reports" />
            </Tabs>
          </Box>

          {/* All Reports Tab */}
          <TabPanel value={tabValue} index={0}>
            {/* Filters */}
            <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
              <TextField
                placeholder="Search reports..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                InputProps={{
                  startAdornment: <Search sx={{ mr: 1, color: 'text.secondary' }} />,
                }}
                sx={{ minWidth: 250 }}
              />
              <FormControl sx={{ minWidth: 150 }}>
                <InputLabel>Type</InputLabel>
                <Select
                  value={filterType}
                  label="Type"
                  onChange={(e) => setFilterType(e.target.value)}
                >
                  <MenuItem value="all">All Types</MenuItem>
                  <MenuItem value="security">Security</MenuItem>
                  <MenuItem value="performance">Performance</MenuItem>
                  <MenuItem value="quality">Quality</MenuItem>
                  <MenuItem value="ai-detection">AI Detection</MenuItem>
                </Select>
              </FormControl>
              <FormControl sx={{ minWidth: 150 }}>
                <InputLabel>Status</InputLabel>
                <Select
                  value={filterStatus}
                  label="Status"
                  onChange={(e) => setFilterStatus(e.target.value)}
                >
                  <MenuItem value="all">All Status</MenuItem>
                  <MenuItem value="completed">Completed</MenuItem>
                  <MenuItem value="in-progress">In Progress</MenuItem>
                  <MenuItem value="failed">Failed</MenuItem>
                </Select>
              </FormControl>
              <Button
                variant="outlined"
                startIcon={<Refresh />}
                onClick={() => {
                  setSearchQuery('');
                  setFilterType('all');
                  setFilterStatus('all');
                }}
              >
                Reset
              </Button>
            </Box>

            {/* Reports Table */}
            <TableContainer component={Paper} variant="outlined">
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Report</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Status</TableCell>
                    <TableCell>Created</TableCell>
                    <TableCell>Issues</TableCell>
                    <TableCell>Duration</TableCell>
                    <TableCell>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {filteredReports.map((report) => (
                    <TableRow
                      key={report.id}
                      hover
                      sx={{ cursor: 'pointer' }}
                      onClick={() => handleReportClick(report)}
                    >
                      <TableCell>
                        <Box>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                            {report.title}
                          </Typography>
                          <Typography variant="body2" color="textSecondary" noWrap>
                            {report.description}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            by {report.createdBy}
                          </Typography>
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getTypeIcon(report.type)}
                          <Chip
                            label={report.type.replace('-', ' ').toUpperCase()}
                            size="small"
                            sx={{
                              backgroundColor: getTypeColor(report.type),
                              color: 'white',
                              fontWeight: 600,
                            }}
                          />
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {getStatusIcon(report.status)}
                          <Chip
                            label={report.status.replace('-', ' ').toUpperCase()}
                            size="small"
                            variant="outlined"
                            sx={{
                              borderColor: getStatusColor(report.status),
                              color: getStatusColor(report.status),
                            }}
                          />
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">
                          {new Date(report.createdAt).toLocaleDateString()}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          {new Date(report.createdAt).toLocaleTimeString()}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {report.issuesFound}
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          {report.filesScanned} files
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2">{report.duration}</Typography>
                        <Typography variant="caption" color="textSecondary">
                          {report.size}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Box sx={{ display: 'flex', gap: 0.5 }}>
                          <Tooltip title="View Report">
                            <IconButton size="small">
                              <Visibility />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Download PDF">
                            <IconButton size="small">
                              <PictureAsPdf />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Export Data">
                            <IconButton size="small">
                              <GetApp />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Share">
                            <IconButton size="small">
                              <Share />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </TabPanel>

          {/* Analytics Tab */}
          <TabPanel value={tabValue} index={1}>
            <Grid container spacing={3}>
              <Grid item xs={12} md={8}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                  Report Trends
                </Typography>
                <ResponsiveContainer width="100%" height={400}>
                  <LineChart data={mockTrendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <RechartsTooltip />
                    <Line type="monotone" dataKey="security" stroke="#d32f2f" strokeWidth={2} />
                    <Line type="monotone" dataKey="performance" stroke="#1976d2" strokeWidth={2} />
                    <Line type="monotone" dataKey="quality" stroke="#388e3c" strokeWidth={2} />
                    <Line type="monotone" dataKey="ai" stroke="#f57c00" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </Grid>
              <Grid item xs={12} md={4}>
                <Typography variant="h6" gutterBottom sx={{ fontWeight: 600 }}>
                  Report Distribution
                </Typography>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                      outerRadius={80}
                      fill="#8884d8"
                      dataKey="value"
                    >
                      {pieData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <RechartsTooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Grid>
            </Grid>
          </TabPanel>

          {/* Scheduled Reports Tab */}
          <TabPanel value={tabValue} index={2}>
            <Box sx={{ textAlign: 'center', py: 8 }}>
              <Schedule sx={{ fontSize: 64, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" gutterBottom>
                Scheduled Reports
              </Typography>
              <Typography variant="body2" color="textSecondary" paragraph>
                Set up automated reports to run on a schedule and receive notifications.
              </Typography>
              <Button variant="contained" size="large">
                Create Scheduled Report
              </Button>
            </Box>
          </TabPanel>
        </CardContent>
      </Card>

      {/* Report Detail Dialog */}
      <Dialog
        open={detailDialogOpen}
        onClose={() => setDetailDialogOpen(false)}
        maxWidth="lg"
        fullWidth
      >
        {selectedReport && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                {getTypeIcon(selectedReport.type)}
                <Box>
                  <Typography variant="h6">{selectedReport.title}</Typography>
                  <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                    <Chip
                      label={selectedReport.type.replace('-', ' ').toUpperCase()}
                      size="small"
                      sx={{
                        backgroundColor: getTypeColor(selectedReport.type),
                        color: 'white',
                      }}
                    />
                    <Chip
                      label={selectedReport.status.replace('-', ' ').toUpperCase()}
                      size="small"
                      variant="outlined"
                      sx={{
                        borderColor: getStatusColor(selectedReport.status),
                        color: getStatusColor(selectedReport.status),
                      }}
                    />
                  </Box>
                </Box>
              </Box>
            </DialogTitle>
            <DialogContent>
              <Grid container spacing={3}>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                    Report Details
                  </Typography>
                  <List>
                    <ListItem>
                      <ListItemText
                        primary="Created By"
                        secondary={selectedReport.createdBy}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Created At"
                        secondary={new Date(selectedReport.createdAt).toLocaleString()}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Duration"
                        secondary={selectedReport.duration}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Report Size"
                        secondary={selectedReport.size}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemText
                        primary="Files Scanned"
                        secondary={selectedReport.filesScanned}
                      />
                    </ListItem>
                  </List>
                </Grid>
                <Grid item xs={12} md={6}>
                  <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                    Issues Summary
                  </Typography>
                  <List>
                    <ListItem>
                      <ListItemIcon>
                        <Error sx={{ color: '#d32f2f' }} />
                      </ListItemIcon>
                      <ListItemText
                        primary="Critical Issues"
                        secondary={selectedReport.severity.critical}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <Warning sx={{ color: '#f57c00' }} />
                      </ListItemIcon>
                      <ListItemText
                        primary="High Priority"
                        secondary={selectedReport.severity.high}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <Warning sx={{ color: '#fbc02d' }} />
                      </ListItemIcon>
                      <ListItemText
                        primary="Medium Priority"
                        secondary={selectedReport.severity.medium}
                      />
                    </ListItem>
                    <ListItem>
                      <ListItemIcon>
                        <CheckCircle sx={{ color: '#388e3c' }} />
                      </ListItemIcon>
                      <ListItemText
                        primary="Low Priority"
                        secondary={selectedReport.severity.low}
                      />
                    </ListItem>
                  </List>
                </Grid>
              </Grid>
              
              <Divider sx={{ my: 3 }} />
              
              <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 600 }}>
                Description
              </Typography>
              <Typography variant="body2" paragraph>
                {selectedReport.description}
              </Typography>
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setDetailDialogOpen(false)}>Close</Button>
              <Button startIcon={<PictureAsPdf />} variant="outlined">
                Download PDF
              </Button>
              <Button startIcon={<GetApp />} variant="contained">
                Export Data
              </Button>
            </DialogActions>
          </>
        )}
      </Dialog>
    </Box>
  );
};

export default Reports;