import React from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Chip,
  IconButton,
  Avatar,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Divider,
  Button,
  Paper,
} from '@mui/material';
import {
  Security as SecurityIcon,
  Speed as SpeedIcon,
  Assessment as AssessmentIcon,
  Psychology as PsychologyIcon,
  TrendingUp,
  TrendingDown,
  Warning,
  CheckCircle,
  Error,
  Info,
  MoreVert,
  Refresh,
} from '@mui/icons-material';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts';

// Mock data for charts
const securityTrendData = [
  { name: 'Jan', vulnerabilities: 12, resolved: 8 },
  { name: 'Feb', vulnerabilities: 8, resolved: 10 },
  { name: 'Mar', vulnerabilities: 15, resolved: 12 },
  { name: 'Apr', vulnerabilities: 6, resolved: 14 },
  { name: 'May', vulnerabilities: 9, resolved: 7 },
  { name: 'Jun', vulnerabilities: 4, resolved: 8 },
];

const codeQualityData = [
  { name: 'Excellent', value: 45, color: '#4caf50' },
  { name: 'Good', value: 30, color: '#2196f3' },
  { name: 'Fair', value: 20, color: '#ff9800' },
  { name: 'Poor', value: 5, color: '#f44336' },
];

const aiDetectionData = [
  { name: 'Mon', detected: 3, total: 25 },
  { name: 'Tue', detected: 7, total: 30 },
  { name: 'Wed', detected: 2, total: 18 },
  { name: 'Thu', detected: 5, total: 22 },
  { name: 'Fri', detected: 8, total: 35 },
  { name: 'Sat', detected: 1, total: 12 },
  { name: 'Sun', detected: 4, total: 20 },
];

interface StatCardProps {
  title: string;
  value: string | number;
  change: number;
  icon: React.ReactElement;
  color: string;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, change, icon, color }) => {
  const isPositive = change > 0;
  const isNegative = change < 0;
  
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            <Typography color="textSecondary" gutterBottom variant="body2">
              {title}
            </Typography>
            <Typography variant="h4" component="div" sx={{ fontWeight: 700 }}>
              {value}
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', mt: 1 }}>
              {isPositive && <TrendingUp sx={{ color: 'success.main', fontSize: 16, mr: 0.5 }} />}
              {isNegative && <TrendingDown sx={{ color: 'error.main', fontSize: 16, mr: 0.5 }} />}
              <Typography
                variant="body2"
                sx={{
                  color: isPositive ? 'success.main' : isNegative ? 'error.main' : 'text.secondary',
                  fontWeight: 600,
                }}
              >
                {change > 0 ? '+' : ''}{change}%
              </Typography>
              <Typography variant="body2" color="textSecondary" sx={{ ml: 0.5 }}>
                vs last month
              </Typography>
            </Box>
          </Box>
          <Avatar
            sx={{
              backgroundColor: color,
              width: 56,
              height: 56,
            }}
          >
            {icon}
          </Avatar>
        </Box>
      </CardContent>
    </Card>
  );
};

interface RecentActivityItem {
  id: string;
  type: 'security' | 'quality' | 'ai' | 'performance';
  message: string;
  timestamp: string;
  severity: 'high' | 'medium' | 'low' | 'info';
}

const recentActivities: RecentActivityItem[] = [
  {
    id: '1',
    type: 'security',
    message: 'SQL injection vulnerability detected in user authentication',
    timestamp: '2 minutes ago',
    severity: 'high',
  },
  {
    id: '2',
    type: 'ai',
    message: 'AI-generated code pattern identified in payment module',
    timestamp: '15 minutes ago',
    severity: 'medium',
  },
  {
    id: '3',
    type: 'quality',
    message: 'Code complexity threshold exceeded in data processing',
    timestamp: '1 hour ago',
    severity: 'medium',
  },
  {
    id: '4',
    type: 'performance',
    message: 'Performance optimization suggestions available',
    timestamp: '2 hours ago',
    severity: 'info',
  },
];

const getActivityIcon = (type: string, severity: string) => {
  const iconProps = { fontSize: 'small' as const };
  
  switch (type) {
    case 'security':
      return <SecurityIcon {...iconProps} />;
    case 'ai':
      return <PsychologyIcon {...iconProps} />;
    case 'quality':
      return <AssessmentIcon {...iconProps} />;
    case 'performance':
      return <SpeedIcon {...iconProps} />;
    default:
      return <Info {...iconProps} />;
  }
};

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'high':
      return 'error';
    case 'medium':
      return 'warning';
    case 'low':
      return 'info';
    default:
      return 'default';
  }
};

const Dashboard: React.FC = () => {
  return (
    <Box sx={{ flexGrow: 1 }}>
      {/* Header */}
      <Box sx={{ mb: 4, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
            Security Dashboard
          </Typography>
          <Typography variant="body1" color="textSecondary">
            Monitor your codebase security, quality, and AI detection in real-time
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={<Refresh />}
          onClick={() => window.location.reload()}
        >
          Refresh Data
        </Button>
      </Box>

      {/* Stats Cards */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Security Issues"
            value={23}
            change={-15}
            icon={<SecurityIcon />}
            color="#f44336"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Code Quality Score"
            value="8.7/10"
            change={5}
            icon={<AssessmentIcon />}
            color="#2196f3"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="AI Detection Rate"
            value="12%"
            change={-3}
            icon={<PsychologyIcon />}
            color="#9c27b0"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Performance Score"
            value="92"
            change={8}
            icon={<SpeedIcon />}
            color="#4caf50"
          />
        </Grid>
      </Grid>

      {/* Charts Row */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Security Trends */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" component="h2" sx={{ fontWeight: 600 }}>
                  Security Vulnerability Trends
                </Typography>
                <IconButton size="small">
                  <MoreVert />
                </IconButton>
              </Box>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={securityTrendData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="vulnerabilities"
                      stroke="#f44336"
                      strokeWidth={2}
                      name="New Vulnerabilities"
                    />
                    <Line
                      type="monotone"
                      dataKey="resolved"
                      stroke="#4caf50"
                      strokeWidth={2}
                      name="Resolved"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Code Quality Distribution */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="h2" sx={{ fontWeight: 600, mb: 2 }}>
                Code Quality Distribution
              </Typography>
              <Box sx={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={codeQualityData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {codeQualityData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </Box>
              <Box sx={{ mt: 2 }}>
                {codeQualityData.map((item) => (
                  <Box key={item.name} sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Box
                      sx={{
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        backgroundColor: item.color,
                        mr: 1,
                      }}
                    />
                    <Typography variant="body2" sx={{ flexGrow: 1 }}>
                      {item.name}
                    </Typography>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      {item.value}%
                    </Typography>
                  </Box>
                ))}
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Bottom Row */}
      <Grid container spacing={3}>
        {/* AI Detection Activity */}
        <Grid item xs={12} md={8}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="h2" sx={{ fontWeight: 600, mb: 2 }}>
                AI Detection Activity
              </Typography>
              <Box sx={{ height: 250 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={aiDetectionData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="total" fill="#e3f2fd" name="Total Files" />
                    <Bar dataKey="detected" fill="#9c27b0" name="AI Detected" />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* Recent Activity */}
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" component="h2" sx={{ fontWeight: 600, mb: 2 }}>
                Recent Activity
              </Typography>
              <List sx={{ p: 0 }}>
                {recentActivities.map((activity, index) => (
                  <React.Fragment key={activity.id}>
                    <ListItem sx={{ px: 0 }}>
                      <ListItemAvatar>
                        <Avatar
                          sx={{
                            width: 32,
                            height: 32,
                            backgroundColor: `${getSeverityColor(activity.severity)}.main`,
                          }}
                        >
                          {getActivityIcon(activity.type, activity.severity)}
                        </Avatar>
                      </ListItemAvatar>
                      <ListItemText
                        primary={
                          <Typography variant="body2" sx={{ fontWeight: 500 }}>
                            {activity.message}
                          </Typography>
                        }
                        secondary={
                          <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
                            <Chip
                              label={activity.severity.toUpperCase()}
                              size="small"
                              color={getSeverityColor(activity.severity) as any}
                              sx={{ mr: 1, fontSize: '0.7rem', height: 20 }}
                            />
                            <Typography variant="caption" color="textSecondary">
                              {activity.timestamp}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                    {index < recentActivities.length - 1 && <Divider />}
                  </React.Fragment>
                ))}
              </List>
              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Button size="small" color="primary">
                  View All Activity
                </Button>
              </Box>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;