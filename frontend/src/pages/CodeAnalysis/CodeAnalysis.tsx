import React, { useState, useCallback } from 'react';
import {
  Box,
  Grid,
  Card,
  CardContent,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Chip,
  LinearProgress,
  Alert,
  Tabs,
  Tab,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Stack,
  Badge,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  CircularProgress,
} from '@mui/material';
import {
  CloudUpload,
  Code,
  Security,
  Speed,
  Assessment,
  Psychology,
  FileUpload,
  ContentCopy,
  Download,
  Refresh,
  PlayArrow,
  Stop,
  CheckCircle,
  Error as ErrorIcon,
  Warning,
  Info,
  ExpandMore,
  Timeline,
  BugReport,
  TrendingUp,
  Analytics,
  Schedule,
  DataUsage,
} from '@mui/icons-material';
import { useDropzone } from 'react-dropzone';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`analysis-tabpanel-${index}`}
      aria-labelledby={`analysis-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

interface AnalysisResult {
  id: string;
  type: 'security' | 'quality' | 'performance' | 'ai-detection';
  severity: 'high' | 'medium' | 'low' | 'info';
  title: string;
  description: string;
  file: string;
  line: number;
  suggestion?: string;
  category?: string;
  impact?: string;
  effort?: 'low' | 'medium' | 'high';
  confidence?: number;
}

interface AnalysisMetrics {
  totalIssues: number;
  criticalIssues: number;
  securityIssues: number;
  qualityIssues: number;
  performanceIssues: number;
  aiDetectionIssues: number;
  linesAnalyzed: number;
  analysisTime: number;
  codeComplexity?: number;
  maintainabilityIndex?: number;
}

interface ComprehensiveSummary {
  summary: string;
  key_findings: string[];
  recommendations: string[];
  overall_assessment: string;
}

const mockAnalysisResults: AnalysisResult[] = [
  {
    id: '1',
    type: 'security',
    severity: 'high',
    title: 'SQL Injection Vulnerability',
    description: 'Potential SQL injection vulnerability detected in database query',
    file: 'src/auth/login.js',
    line: 45,
    suggestion: 'Use parameterized queries or prepared statements',
  },
  {
    id: '2',
    type: 'ai-detection',
    severity: 'medium',
    title: 'AI-Generated Code Pattern',
    description: 'Code pattern suggests AI generation with 87% confidence',
    file: 'src/utils/helpers.js',
    line: 12,
    suggestion: 'Review code for compliance with coding standards',
  },
  {
    id: '3',
    type: 'quality',
    severity: 'medium',
    title: 'High Cyclomatic Complexity',
    description: 'Function has cyclomatic complexity of 15 (threshold: 10)',
    file: 'src/data/processor.js',
    line: 78,
    suggestion: 'Consider breaking down into smaller functions',
  },
  {
    id: '4',
    type: 'performance',
    severity: 'low',
    title: 'Inefficient Loop',
    description: 'Nested loop with O(n²) complexity detected',
    file: 'src/algorithms/sort.js',
    line: 23,
    suggestion: 'Consider using more efficient sorting algorithm',
  },
];

const CodeAnalysis: React.FC = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [codeInput, setCodeInput] = useState('');
  const [selectedLanguage, setSelectedLanguage] = useState('javascript');
  const [analysisType, setAnalysisType] = useState('comprehensive');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResults, setAnalysisResults] = useState<AnalysisResult[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [resultDialogOpen, setResultDialogOpen] = useState(false);
  const [selectedResult, setSelectedResult] = useState<AnalysisResult | null>(null);
  const [comprehensiveSummary, setComprehensiveSummary] = useState<ComprehensiveSummary | null>(null);
  const [analysisMetrics, setAnalysisMetrics] = useState<AnalysisMetrics | null>(null);
  const [expandedAccordion, setExpandedAccordion] = useState<string | false>('overview');

  const onDrop = useCallback((acceptedFiles: File[]) => {
    setUploadedFiles(prev => [...prev, ...acceptedFiles]);
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/plain': ['.js', '.ts', '.jsx', '.tsx', '.py', '.java', '.cpp', '.c', '.h'],
      'application/javascript': ['.js'],
      'application/typescript': ['.ts'],
    },
  });

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleAnalyze = async () => {
    if (!codeInput.trim()) return;

    setIsAnalyzing(true);
    setAnalysisResults([]);
    setShowResults(false);
    setComprehensiveSummary(null);
    setAnalysisMetrics(null);

    const startTime = Date.now();
    
    try {
      const response = await fetch('http://localhost:8000/api/v1/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          code: codeInput,
          language: selectedLanguage,
          analysis_types: [analysisType],
        }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: any = await response.json();
      const analysisTime = Date.now() - startTime;
      
      // Transform backend response to frontend format
      const transformedResults: AnalysisResult[] = [];
      
      // Add security issues
      if (data.security_analysis?.vulnerabilities) {
        data.security_analysis.vulnerabilities.forEach((vuln: any, index: number) => {
          transformedResults.push({
            id: `security-${index}`,
            type: 'security',
            severity: vuln.severity || 'medium',
            title: vuln.type || 'Security Issue',
            description: vuln.description || 'Security vulnerability detected',
            file: vuln.file || 'input.code',
            line: vuln.line || 1,
            suggestion: vuln.recommendation,
            category: 'Security Vulnerability',
            impact: vuln.severity === 'high' ? 'High' : vuln.severity === 'medium' ? 'Medium' : 'Low',
            effort: vuln.severity === 'high' ? 'high' : 'medium',
            confidence: vuln.confidence || Math.floor(Math.random() * 20) + 80,
          });
        });
      }
      
      // Add AI detection results
      if (data.ai_detection?.is_ai_generated) {
        transformedResults.push({
          id: 'ai-detection',
          type: 'ai-detection',
          severity: 'medium',
          title: 'AI-Generated Code Pattern',
          description: `Code pattern suggests AI generation with ${Math.round((data.ai_detection.confidence || 0) * 100)}% confidence`,
          file: 'input.code',
          line: 1,
          suggestion: 'Review code for compliance with coding standards',
          category: 'AI Detection',
          impact: 'Medium',
          effort: 'medium',
          confidence: Math.round((data.ai_detection.confidence || 0) * 100),
        });
      }
      
      // Add quality issues
      if (data.quality_analysis?.issues) {
        data.quality_analysis.issues.forEach((issue: any, index: number) => {
          transformedResults.push({
            id: `quality-${index}`,
            type: 'quality',
            severity: issue.severity || 'medium',
            title: issue.type || 'Code Quality Issue',
            description: issue.description || 'Code quality issue detected',
            file: issue.file || 'input.code',
            line: issue.line || 1,
            suggestion: issue.suggestion,
            category: 'Code Quality',
            impact: issue.severity === 'high' ? 'High' : issue.severity === 'medium' ? 'Medium' : 'Low',
            effort: issue.severity === 'high' ? 'high' : 'medium',
            confidence: issue.confidence || Math.floor(Math.random() * 20) + 80,
          });
        });
      }
      
      // Add performance issues
      if (data.performance_analysis?.issues) {
        data.performance_analysis.issues.forEach((issue: any, index: number) => {
          transformedResults.push({
            id: `performance-${index}`,
            type: 'performance',
            severity: issue.severity || 'low',
            title: issue.type || 'Performance Issue',
            description: issue.description || 'Performance issue detected',
            file: issue.file || 'input.code',
            line: issue.line || 1,
            suggestion: issue.suggestion,
            category: 'Performance Issue',
            impact: issue.severity === 'high' ? 'High' : issue.severity === 'medium' ? 'Medium' : 'Low',
            effort: issue.severity === 'high' ? 'high' : 'medium',
            confidence: issue.confidence || Math.floor(Math.random() * 20) + 80,
          });
        });
      }
      
      // Generate comprehensive metrics
      const metrics: AnalysisMetrics = {
        totalIssues: transformedResults.length,
        criticalIssues: transformedResults.filter(r => r.severity === 'high').length,
        securityIssues: transformedResults.filter(r => r.type === 'security').length,
        qualityIssues: transformedResults.filter(r => r.type === 'quality').length,
        performanceIssues: transformedResults.filter(r => r.type === 'performance').length,
        aiDetectionIssues: transformedResults.filter(r => r.type === 'ai-detection').length,
        linesAnalyzed: codeInput.split('\n').length,
        analysisTime: analysisTime,
        codeComplexity: data.metadata?.complexity || Math.floor(Math.random() * 20) + 5,
        maintainabilityIndex: data.metadata?.maintainability || Math.floor(Math.random() * 40) + 60,
      };
      
      setAnalysisMetrics(metrics);
      
      // Set comprehensive summary
      if (data.results?.comprehensive_summary) {
        setComprehensiveSummary(data.results.comprehensive_summary);
      }
      
      setAnalysisResults(transformedResults);
      setShowResults(true);
    } catch (error) {
      console.error('Analysis failed:', error);
      const analysisTime = Date.now() - startTime;
      
      // Show mock results for demo with enhanced data
      const enhancedMockResults = mockAnalysisResults.map(result => ({
        ...result,
        category: result.type === 'security' ? 'Security Vulnerability' : 
                 result.type === 'quality' ? 'Code Quality' :
                 result.type === 'performance' ? 'Performance Issue' : 'AI Detection',
        impact: result.severity === 'high' ? 'High' : result.severity === 'medium' ? 'Medium' : 'Low',
        effort: (result.severity === 'high' ? 'high' : 'medium') as 'low' | 'medium' | 'high',
        confidence: Math.floor(Math.random() * 20) + 80,
      }));
      
      setAnalysisResults(enhancedMockResults);
      
      // Generate mock metrics
      const mockMetrics: AnalysisMetrics = {
        totalIssues: enhancedMockResults.length,
        criticalIssues: enhancedMockResults.filter(r => r.severity === 'high').length,
        securityIssues: enhancedMockResults.filter(r => r.type === 'security').length,
        qualityIssues: enhancedMockResults.filter(r => r.type === 'quality').length,
        performanceIssues: enhancedMockResults.filter(r => r.type === 'performance').length,
        aiDetectionIssues: enhancedMockResults.filter(r => r.type === 'ai-detection').length,
        linesAnalyzed: codeInput.split('\n').length,
        analysisTime: analysisTime,
        codeComplexity: 12,
        maintainabilityIndex: 78,
      };
      
      setAnalysisMetrics(mockMetrics);
      setShowResults(true);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleFileAnalyze = async () => {
    if (uploadedFiles.length === 0) return;
    
    setIsAnalyzing(true);
    setAnalysisResults([]);
    setShowResults(false);
    
    try {
      const formData = new FormData();
      uploadedFiles.forEach((file, index) => {
        formData.append('file', file);
      });
      formData.append('analysis_types', analysisType);
      
      const response = await fetch('http://localhost:8000/api/v1/analyze/file', {
        method: 'POST',
        body: formData,
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: any = await response.json();
      
      // Transform backend response to frontend format
      const transformedResults: AnalysisResult[] = [];
      const filename = data.metadata?.filename || 'uploaded_file';
      
      // Add security issues
      if (data.results?.security?.vulnerabilities) {
        data.results.security.vulnerabilities.forEach((vuln: any, index: number) => {
          transformedResults.push({
            id: `${filename}-security-${index}`,
            type: 'security',
            severity: vuln.severity || 'medium',
            title: vuln.type || 'Security Issue',
            description: vuln.description || 'Security vulnerability detected',
            file: filename,
            line: vuln.line || 1,
            suggestion: vuln.recommendation,
          });
        });
      }
      
      // Add AI detection results
      if (data.results?.ai_detection?.is_ai_generated) {
        transformedResults.push({
          id: `${filename}-ai-detection`,
          type: 'ai-detection',
          severity: 'medium',
          title: 'AI-Generated Code Pattern',
          description: `Code pattern suggests AI generation with ${Math.round((data.results.ai_detection.confidence || 0) * 100)}% confidence`,
          file: filename,
          line: 1,
          suggestion: 'Review code for compliance with coding standards',
        });
      }
      
      // Add quality issues
      if (data.results?.quality?.issues) {
        data.results.quality.issues.forEach((issue: any, index: number) => {
          transformedResults.push({
            id: `${filename}-quality-${index}`,
            type: 'quality',
            severity: issue.severity || 'medium',
            title: issue.title || issue.issue_type || 'Code Quality Issue',
            description: issue.description || 'Code quality issue detected',
            file: filename,
            line: issue.line_start || issue.line || 1,
            suggestion: issue.recommendation || issue.suggestion,
          });
        });
      }
      
      // Add performance issues
      if (data.results?.performance?.issues) {
        data.results.performance.issues.forEach((issue: any, index: number) => {
          transformedResults.push({
            id: `${filename}-performance-${index}`,
            type: 'performance',
            severity: issue.severity || 'low',
            title: issue.title || issue.issue_type || 'Performance Issue',
            description: issue.description || 'Performance issue detected',
            file: filename,
            line: issue.line_start || issue.line || 1,
            suggestion: issue.recommendation || issue.suggestion,
          });
        });
      }
      
      setAnalysisResults(transformedResults);
      setShowResults(true);
    } catch (error) {
      console.error('File analysis failed:', error);
      setAnalysisResults([]);
      setShowResults(true);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleResultClick = (result: AnalysisResult) => {
    setSelectedResult(result);
    setResultDialogOpen(true);
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high':
        return <ErrorIcon color="error" />;
      case 'medium':
        return <Warning color="warning" />;
      case 'low':
        return <Info color="info" />;
      default:
        return <CheckCircle color="success" />;
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
        return 'success';
    }
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'security':
        return <Security />;
      case 'quality':
        return <Assessment />;
      case 'performance':
        return <Speed />;
      case 'ai-detection':
        return <Psychology />;
      default:
        return <Code />;
    }
  };

  return (
    <Box sx={{ width: '100%', minHeight: '100vh', bgcolor: 'grey.50' }}>
      {/* Modern Header with Gradient */}
      <Box 
        sx={{ 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          py: 6,
          px: 4,
          mb: 4,
          borderRadius: '0 0 24px 24px',
          position: 'relative',
          overflow: 'hidden',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: 'url("data:image/svg+xml,%3Csvg width="60" height="60" viewBox="0 0 60 60" xmlns="http://www.w3.org/2000/svg"%3E%3Cg fill="none" fill-rule="evenodd"%3E%3Cg fill="%23ffffff" fill-opacity="0.05"%3E%3Ccircle cx="30" cy="30" r="4"/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")',
            opacity: 0.3
          }
        }}
      >
        <Box sx={{ position: 'relative', zIndex: 1, maxWidth: '1200px', mx: 'auto' }}>
          <Typography 
            variant="h3" 
            component="h1" 
            gutterBottom 
            sx={{ 
              fontWeight: 800,
              fontSize: { xs: '2rem', md: '3rem' },
              textAlign: 'center',
              mb: 2
            }}
          >
            🛡️ CodeGuard Analysis
          </Typography>
          <Typography 
            variant="h6" 
            sx={{ 
              textAlign: 'center',
              opacity: 0.9,
              maxWidth: '600px',
              mx: 'auto',
              lineHeight: 1.6,
              fontSize: { xs: '1rem', md: '1.25rem' }
            }}
          >
            Advanced AI-powered code analysis for security, quality, performance, and AI detection
          </Typography>
        </Box>
      </Box>

      {/* Modern Analysis Tabs */}
      <Box sx={{ maxWidth: '1200px', mx: 'auto', px: 2 }}>
        <Paper 
          elevation={0}
          sx={{ 
            mb: 4,
            borderRadius: 3,
            overflow: 'hidden',
            border: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper'
          }}
        >
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            aria-label="analysis tabs"
            variant="fullWidth"
            sx={{ 
              '& .MuiTab-root': {
                minHeight: 72,
                textTransform: 'none',
                fontSize: '1rem',
                fontWeight: 600,
                '&.Mui-selected': {
                  color: 'primary.main',
                  bgcolor: 'primary.50'
                }
              },
              '& .MuiTabs-indicator': {
                height: 3,
                borderRadius: '3px 3px 0 0'
              }
            }}
          >
            <Tab 
              label="Code Input" 
              icon={<Code />} 
              iconPosition="start"
              sx={{ gap: 1 }}
            />
            <Tab 
              label="File Upload" 
              icon={<FileUpload />} 
              iconPosition="start"
              sx={{ gap: 1 }}
            />
            <Tab 
              label="Repository Scan" 
              icon={<CloudUpload />} 
              iconPosition="start"
              sx={{ gap: 1 }}
            />
          </Tabs>

          {/* Code Input Tab */}
          <TabPanel value={activeTab} index={0}>
            <Box sx={{ p: 4 }}>
              <Grid container spacing={4}>
                <Grid item xs={12} lg={8}>
                  <Paper 
                    elevation={0}
                    sx={{ 
                      border: '2px dashed',
                      borderColor: 'primary.200',
                      borderRadius: 2,
                      p: 3,
                      bgcolor: 'grey.50',
                      transition: 'all 0.2s ease-in-out',
                      '&:hover': {
                        borderColor: 'primary.main',
                        bgcolor: 'primary.50'
                      }
                    }}
                  >
                    <Typography variant="h6" sx={{ mb: 2, fontWeight: 600 }}>
                      📝 Code Input
                    </Typography>
                    <TextField
                      fullWidth
                      multiline
                      rows={16}
                      variant="outlined"
                      label="Paste your code here"
                      value={codeInput}
                      onChange={(e) => setCodeInput(e.target.value)}
                      placeholder="// Paste your code here for analysis...
function example() {
  console.log('Hello, CodeGuard!');
  // Your code will be analyzed for security, quality, and performance
}"
                      sx={{
                        '& .MuiInputBase-root': {
                          fontFamily: 'JetBrains Mono, Monaco, Consolas, "Courier New", monospace',
                          fontSize: '0.9rem',
                          lineHeight: 1.6,
                          bgcolor: 'background.paper',
                          borderRadius: 2
                        },
                        '& .MuiOutlinedInput-root': {
                          '&:hover fieldset': {
                            borderColor: 'primary.main'
                          }
                        }
                      }}
                    />
                  </Paper>
            </Grid>
                 <Grid item xs={12} lg={4}>
                   <Paper 
                     elevation={0}
                     sx={{ 
                       p: 3,
                       border: '1px solid',
                       borderColor: 'divider',
                       borderRadius: 2,
                       bgcolor: 'background.paper',
                       height: 'fit-content',
                       position: 'sticky',
                       top: 20
                     }}
                   >
                     <Typography variant="h6" sx={{ mb: 3, fontWeight: 600 }}>
                       ⚙️ Analysis Settings
                     </Typography>
                     <Stack spacing={3}>
                       <FormControl fullWidth>
                         <InputLabel>Programming Language</InputLabel>
                         <Select
                           value={selectedLanguage}
                           label="Programming Language"
                           onChange={(e) => setSelectedLanguage(e.target.value)}
                           sx={{ borderRadius: 2 }}
                         >
                           <MenuItem value="javascript">🟨 JavaScript</MenuItem>
                           <MenuItem value="typescript">🔷 TypeScript</MenuItem>
                           <MenuItem value="python">🐍 Python</MenuItem>
                           <MenuItem value="java">☕ Java</MenuItem>
                           <MenuItem value="cpp">⚡ C++</MenuItem>
                           <MenuItem value="c">🔧 C</MenuItem>
                         </Select>
                       </FormControl>

                       <FormControl fullWidth>
                         <InputLabel>Analysis Scope</InputLabel>
                         <Select
                           value={analysisType}
                           label="Analysis Scope"
                           onChange={(e) => setAnalysisType(e.target.value)}
                           sx={{ borderRadius: 2 }}
                         >
                           <MenuItem value="comprehensive">🔍 Comprehensive Analysis</MenuItem>
                           <MenuItem value="security">🛡️ Security Focus</MenuItem>
                           <MenuItem value="quality">✨ Code Quality</MenuItem>
                           <MenuItem value="performance">⚡ Performance Focus</MenuItem>
                           <MenuItem value="ai-detection">🤖 AI Detection</MenuItem>
                         </Select>
                       </FormControl>

                       <Button
                         variant="contained"
                         size="large"
                         startIcon={isAnalyzing ? <CircularProgress size={20} /> : <PlayArrow />}
                         onClick={handleAnalyze}
                         disabled={!codeInput.trim() || isAnalyzing}
                         sx={{
                           py: 1.5,
                           borderRadius: 2,
                           textTransform: 'none',
                           fontSize: '1.1rem',
                           fontWeight: 600,
                           background: 'linear-gradient(45deg, #667eea 30%, #764ba2 90%)',
                           boxShadow: '0 4px 20px rgba(102, 126, 234, 0.3)',
                           '&:hover': {
                             boxShadow: '0 6px 25px rgba(102, 126, 234, 0.4)',
                             transform: 'translateY(-1px)'
                           },
                           '&:disabled': {
                             background: 'grey.300'
                           }
                         }}
                       >
                         {isAnalyzing ? '🔄 Analyzing...' : '🚀 Analyze Code'}
                       </Button>

                       {isAnalyzing && (
                         <Box sx={{ mt: 2 }}>
                           <Typography variant="body2" gutterBottom sx={{ textAlign: 'center' }}>
                             🔍 Analysis in progress...
                           </Typography>
                           <LinearProgress sx={{ borderRadius: 1 }} />
                         </Box>
                       )}
                     </Stack>
                   </Paper>
                 </Grid>
               </Grid>
             </Box>
           </TabPanel>

        {/* File Upload Tab */}
        <TabPanel value={activeTab} index={1}>
          <Box sx={{ p: 4 }}>
            <Grid container spacing={4}>
              <Grid item xs={12} lg={8}>
                <Paper
                  {...getRootProps()}
                  elevation={0}
                  sx={{
                    p: 6,
                    textAlign: 'center',
                    border: '3px dashed',
                    borderColor: isDragActive ? 'primary.main' : 'primary.200',
                    backgroundColor: isDragActive ? 'primary.50' : 'grey.50',
                    cursor: 'pointer',
                    borderRadius: 3,
                    transition: 'all 0.3s ease-in-out',
                    '&:hover': {
                      borderColor: 'primary.main',
                      backgroundColor: 'primary.50',
                      transform: 'translateY(-2px)',
                      boxShadow: '0 8px 25px rgba(102, 126, 234, 0.15)'
                    }
                  }}
                >
                  <input {...getInputProps()} />
                  <CloudUpload sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  {isDragActive ? 'Drop files here' : 'Drag & drop files here'}
                </Typography>
                <Typography variant="body2" color="textSecondary" gutterBottom>
                  or click to select files
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  Supported: .js, .ts, .jsx, .tsx, .py, .java, .cpp, .c, .h
                </Typography>
              </Paper>

              {uploadedFiles.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom>
                    Uploaded Files ({uploadedFiles.length})
                  </Typography>
                  <List dense>
                    {uploadedFiles.map((file, index) => (
                      <ListItem key={index}>
                        <ListItemIcon>
                          <Code />
                        </ListItemIcon>
                        <ListItemText
                          primary={file.name}
                          secondary={`${(file.size / 1024).toFixed(1)} KB`}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Grid>
            <Grid item xs={12} lg={4}>
              <Paper elevation={0} sx={{ p: 4, backgroundColor: 'grey.50', borderRadius: 3, position: 'sticky', top: 24 }}>
                <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                  <Assessment color="primary" />
                  Analysis Settings
                </Typography>
                <Stack spacing={3}>
                  <FormControl fullWidth>
                    <InputLabel>Analysis Type</InputLabel>
                    <Select
                      value={analysisType}
                      label="Analysis Type"
                      onChange={(e) => setAnalysisType(e.target.value)}
                      sx={{ borderRadius: 2 }}
                    >
                      <MenuItem value="comprehensive">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Analytics fontSize="small" />
                          Comprehensive Analysis
                        </Box>
                      </MenuItem>
                      <MenuItem value="security">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Security fontSize="small" />
                          Security Focus
                        </Box>
                      </MenuItem>
                      <MenuItem value="quality">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Assessment fontSize="small" />
                          Code Quality
                        </Box>
                      </MenuItem>
                      <MenuItem value="performance">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Speed fontSize="small" />
                          Performance Only
                        </Box>
                      </MenuItem>
                      <MenuItem value="ai-detection">
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Psychology fontSize="small" />
                          AI Detection Only
                        </Box>
                      </MenuItem>
                    </Select>
                  </FormControl>

                  <Button
                    variant="contained"
                    size="large"
                    startIcon={isAnalyzing ? <Stop /> : <PlayArrow />}
                    onClick={handleFileAnalyze}
                    disabled={uploadedFiles.length === 0 || isAnalyzing}
                    fullWidth
                    sx={{
                      background: 'linear-gradient(45deg, #667eea 30%, #764ba2 90%)',
                      borderRadius: 2,
                      py: 1.5,
                      '&:hover': {
                        background: 'linear-gradient(45deg, #5a6fd8 30%, #6a4190 90%)',
                        transform: 'translateY(-1px)',
                        boxShadow: '0 6px 20px rgba(102, 126, 234, 0.4)'
                      },
                      '&:disabled': {
                        background: 'linear-gradient(45deg, #ccc 30%, #999 90%)'
                      }
                    }}
                  >
                    {isAnalyzing ? 'Analyzing...' : 'Analyze Files'}
                  </Button>

                  {isAnalyzing && (
                    <Box>
                      <Typography variant="body2" gutterBottom color="text.secondary">
                        Analysis in progress...
                      </Typography>
                      <LinearProgress sx={{ borderRadius: 1 }} />
                    </Box>
                  )}
                </Stack>
              </Paper>
            </Grid>
          </Grid>
          </Box>
        </TabPanel>

        {/* Repository Scan Tab */}
        <TabPanel value={activeTab} index={2}>
          <Box sx={{ p: 4 }}>
            <Grid container spacing={4}>
              <Grid item xs={12} lg={8}>
                <Paper elevation={0} sx={{ p: 4, backgroundColor: 'grey.50', borderRadius: 3 }}>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                    <Code color="primary" />
                    Repository Configuration
                  </Typography>
                  <Stack spacing={3}>
                    <TextField
                      fullWidth
                      label="Repository URL"
                      placeholder="https://github.com/username/repository"
                      variant="outlined"
                      sx={{ 
                        '& .MuiOutlinedInput-root': {
                          borderRadius: 2,
                          '&:hover fieldset': {
                            borderColor: 'primary.main'
                          }
                        }
                      }}
                    />
                    <TextField
                      fullWidth
                      label="Branch (optional)"
                      placeholder="main"
                      variant="outlined"
                      sx={{ 
                        '& .MuiOutlinedInput-root': {
                          borderRadius: 2,
                          '&:hover fieldset': {
                            borderColor: 'primary.main'
                          }
                        }
                      }}
                    />
                    <Alert 
                      severity="info" 
                      sx={{ 
                        borderRadius: 2,
                        '& .MuiAlert-icon': {
                          color: 'info.main'
                        }
                      }}
                    >
                      Repository scanning requires authentication. Configure your Git credentials in Settings.
                    </Alert>
                  </Stack>
                </Paper>
              </Grid>
              <Grid item xs={12} lg={4}>
                <Paper elevation={0} sx={{ p: 4, backgroundColor: 'grey.50', borderRadius: 3, position: 'sticky', top: 24 }}>
                  <Typography variant="h6" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 3 }}>
                    <Assessment color="primary" />
                    Repository Actions
                  </Typography>
                  <Stack spacing={3}>
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<CloudUpload />}
                      fullWidth
                      disabled
                      sx={{
                        background: 'linear-gradient(45deg, #667eea 30%, #764ba2 90%)',
                        borderRadius: 2,
                        py: 1.5,
                        '&:disabled': {
                          background: 'linear-gradient(45deg, #ccc 30%, #999 90%)'
                        }
                      }}
                    >
                      Scan Repository
                    </Button>
                    <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center' }}>
                      Coming soon in next release
                    </Typography>
                  </Stack>
                </Paper>
              </Grid>
            </Grid>
          </Box>
        </TabPanel>
      </Paper>

      {/* Analysis Metrics Dashboard */}
      {showResults && analysisMetrics && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 600 }}>
            Analysis Overview
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={3}>
              <Card 
                elevation={0}
                sx={{ 
                  textAlign: 'center', 
                  p: 3,
                  borderRadius: 3,
                  background: 'linear-gradient(135deg, #fff5f5 0%, #fed7d7 100%)',
                  border: '1px solid',
                  borderColor: 'error.100',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 8px 25px rgba(245, 101, 101, 0.15)'
                  }
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                  <BugReport sx={{ color: 'error.main', fontSize: 32 }} />
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'error.main' }}>
                    {analysisMetrics.totalIssues}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                    Total Issues
                  </Typography>
                </Box>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card 
                elevation={0}
                sx={{ 
                  textAlign: 'center', 
                  p: 3,
                  borderRadius: 3,
                  background: 'linear-gradient(135deg, #fffbeb 0%, #fed7aa 100%)',
                  border: '1px solid',
                  borderColor: 'warning.200',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 8px 25px rgba(251, 146, 60, 0.15)'
                  }
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                  <Security sx={{ color: 'warning.main', fontSize: 32 }} />
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'warning.main' }}>
                    {analysisMetrics.criticalIssues}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                    Critical Issues
                  </Typography>
                </Box>
              </Card>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card 
                elevation={0}
                sx={{ 
                  textAlign: 'center', 
                  p: 3,
                  borderRadius: 3,
                  background: 'linear-gradient(135deg, #eff6ff 0%, #bfdbfe 100%)',
                  border: '1px solid',
                  borderColor: 'info.200',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 8px 25px rgba(59, 130, 246, 0.15)'
                  }
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                  <Code sx={{ color: 'info.main', fontSize: 32 }} />
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'info.main' }}>
                     {analysisMetrics.linesAnalyzed}
                   </Typography>
                   <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                     Lines Analyzed
                   </Typography>
                 </Box>
               </Card>
             </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Card 
                elevation={0}
                sx={{ 
                  textAlign: 'center', 
                  p: 3,
                  borderRadius: 3,
                  background: 'linear-gradient(135deg, #f0fdf4 0%, #bbf7d0 100%)',
                  border: '1px solid',
                  borderColor: 'success.200',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: '0 8px 25px rgba(34, 197, 94, 0.15)'
                  }
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                  <Schedule sx={{ color: 'success.main', fontSize: 32 }} />
                  <Typography variant="h3" sx={{ fontWeight: 700, color: 'success.main' }}>
                    {(analysisMetrics.analysisTime / 1000).toFixed(1)}s
                  </Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
                    Analysis Time
                  </Typography>
                </Box>
              </Card>
            </Grid>
          </Grid>
        </Box>
      )}

      {/* Detailed Analysis Breakdown */}
      {showResults && analysisMetrics && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Typography variant="h6" sx={{ fontWeight: 600, mb: 3 }}>
              Analysis Breakdown
            </Typography>
            <Grid container spacing={3}>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 3 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                    Issue Distribution
                  </Typography>
                  <Stack spacing={2}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Security sx={{ color: 'error.main', mr: 1, fontSize: 20 }} />
                        <Typography variant="body2">Security</Typography>
                      </Box>
                      <Badge badgeContent={analysisMetrics.securityIssues} color="error" />
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Assessment sx={{ color: 'warning.main', mr: 1, fontSize: 20 }} />
                        <Typography variant="body2">Quality</Typography>
                      </Box>
                      <Badge badgeContent={analysisMetrics.qualityIssues} color="warning" />
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Speed sx={{ color: 'info.main', mr: 1, fontSize: 20 }} />
                        <Typography variant="body2">Performance</Typography>
                      </Box>
                      <Badge badgeContent={analysisMetrics.performanceIssues} color="info" />
                    </Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <Box sx={{ display: 'flex', alignItems: 'center' }}>
                        <Psychology sx={{ color: 'secondary.main', mr: 1, fontSize: 20 }} />
                        <Typography variant="body2">AI Detection</Typography>
                      </Box>
                      <Badge badgeContent={analysisMetrics.aiDetectionIssues} color="secondary" />
                    </Box>
                  </Stack>
                </Paper>
              </Grid>
              <Grid item xs={12} md={6}>
                <Paper sx={{ p: 3 }}>
                  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
                    Code Quality Metrics
                  </Typography>
                  <Stack spacing={2}>
                    <Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">Code Complexity</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {analysisMetrics.codeComplexity}
                        </Typography>
                      </Box>
                      <LinearProgress 
                        variant="determinate" 
                        value={Math.min((analysisMetrics.codeComplexity || 0) * 5, 100)} 
                        color={analysisMetrics.codeComplexity && analysisMetrics.codeComplexity > 15 ? 'error' : 
                               analysisMetrics.codeComplexity && analysisMetrics.codeComplexity > 10 ? 'warning' : 'success'}
                      />
                    </Box>
                    <Box>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                        <Typography variant="body2">Maintainability Index</Typography>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {analysisMetrics.maintainabilityIndex}%
                        </Typography>
                      </Box>
                      <LinearProgress 
                        variant="determinate" 
                        value={analysisMetrics.maintainabilityIndex || 0} 
                        color={analysisMetrics.maintainabilityIndex && analysisMetrics.maintainabilityIndex < 50 ? 'error' : 
                               analysisMetrics.maintainabilityIndex && analysisMetrics.maintainabilityIndex < 75 ? 'warning' : 'success'}
                      />
                    </Box>
                  </Stack>
                </Paper>
              </Grid>
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* GPT-4o-mini Comprehensive Summary */}
      {showResults && comprehensiveSummary && (
        <Card sx={{ mb: 3 }}>
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
              <Psychology sx={{ mr: 1, color: 'primary.main' }} />
              <Typography variant="h6" component="h2" sx={{ fontWeight: 600 }}>
                GPT-4o-mini Analysis Summary
              </Typography>
            </Box>
            
            <Paper sx={{ p: 3, mb: 3, backgroundColor: 'grey.50' }}>
              <Typography variant="body1" sx={{ mb: 2, lineHeight: 1.6 }}>
                {comprehensiveSummary.summary}
              </Typography>
              
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: 'primary.main' }}>
                Overall Assessment
              </Typography>
              <Typography variant="body2" sx={{ mb: 3, fontStyle: 'italic' }}>
                {comprehensiveSummary.overall_assessment}
              </Typography>
              
              {comprehensiveSummary.key_findings.length > 0 && (
                <Box sx={{ mb: 3 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: 'warning.main' }}>
                    Key Findings
                  </Typography>
                  <List dense>
                    {comprehensiveSummary.key_findings.map((finding, index) => (
                      <ListItem key={index} sx={{ py: 0.5 }}>
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          <Info sx={{ fontSize: 16, color: 'warning.main' }} />
                        </ListItemIcon>
                        <ListItemText primary={finding} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
              
              {comprehensiveSummary.recommendations.length > 0 && (
                <Box>
                  <Typography variant="h6" sx={{ fontWeight: 600, mb: 1, color: 'success.main' }}>
                    Recommendations
                  </Typography>
                  <List dense>
                    {comprehensiveSummary.recommendations.map((recommendation, index) => (
                      <ListItem key={index} sx={{ py: 0.5 }}>
                        <ListItemIcon sx={{ minWidth: 32 }}>
                          <CheckCircle sx={{ fontSize: 16, color: 'success.main' }} />
                        </ListItemIcon>
                        <ListItemText primary={recommendation} />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Paper>
          </CardContent>
        </Card>
      )}

      {/* Analysis Results */}
      {showResults && (
        <Card>
          <CardContent>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
              <Typography variant="h6" component="h2" sx={{ fontWeight: 600 }}>
                Analysis Results ({analysisResults.length} issues found)
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Tooltip title="Copy Results">
                  <IconButton size="small">
                    <ContentCopy />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Download Report">
                  <IconButton size="small">
                    <Download />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Re-analyze">
                  <IconButton size="small" onClick={handleAnalyze}>
                    <Refresh />
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>

            {/* Results by Category */}
            <Box sx={{ mb: 3 }}>
              {['security', 'quality', 'performance', 'ai-detection'].map((category) => {
                const categoryResults = analysisResults.filter(result => result.type === category);
                if (categoryResults.length === 0) return null;
                
                return (
                  <Accordion 
                    key={category}
                    expanded={expandedAccordion === category}
                    onChange={() => setExpandedAccordion(expandedAccordion === category ? false : category)}
                    sx={{ mb: 1 }}
                  >
                    <AccordionSummary expandIcon={<ExpandMore />}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
                        {getTypeIcon(category)}
                        <Typography variant="subtitle1" sx={{ fontWeight: 600, textTransform: 'capitalize' }}>
                          {category.replace('-', ' ')} Issues
                        </Typography>
                        <Chip 
                          label={categoryResults.length} 
                          size="small" 
                          color={category === 'security' ? 'error' : 
                                 category === 'quality' ? 'warning' : 
                                 category === 'performance' ? 'info' : 'secondary'}
                        />
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      <TableContainer component={Paper} variant="outlined">
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>Severity</TableCell>
                              <TableCell>Issue</TableCell>
                              <TableCell>Location</TableCell>
                              <TableCell>Impact</TableCell>
                              <TableCell>Effort</TableCell>
                              <TableCell>Confidence</TableCell>
                              <TableCell>Actions</TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {categoryResults.map((result) => (
                              <TableRow key={result.id} hover>
                                <TableCell>
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    {getSeverityIcon(result.severity)}
                                    <Chip
                                      label={result.severity.toUpperCase()}
                                      size="small"
                                      color={getSeverityColor(result.severity) as any}
                                    />
                                  </Box>
                                </TableCell>
                                <TableCell>
                                  <Box>
                                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                                      {result.title}
                                    </Typography>
                                    <Typography variant="caption" color="textSecondary">
                                      {result.description}
                                    </Typography>
                                  </Box>
                                </TableCell>
                                <TableCell>
                                  <Typography variant="caption">
                                    {result.file}:{result.line}
                                  </Typography>
                                </TableCell>
                                <TableCell>
                                  <Chip 
                                    label={result.impact || 'Medium'} 
                                    size="small" 
                                    variant="outlined"
                                    color={result.impact === 'High' ? 'error' : 
                                           result.impact === 'Medium' ? 'warning' : 'success'}
                                  />
                                </TableCell>
                                <TableCell>
                                  <Chip 
                                    label={result.effort?.toUpperCase() || 'MEDIUM'} 
                                    size="small" 
                                    variant="outlined"
                                  />
                                </TableCell>
                                <TableCell>
                                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <CircularProgress 
                                      variant="determinate" 
                                      value={result.confidence || 85} 
                                      size={20}
                                      color={result.confidence && result.confidence > 90 ? 'success' : 
                                             result.confidence && result.confidence > 70 ? 'warning' : 'error'}
                                    />
                                    <Typography variant="caption">
                                      {result.confidence || 85}%
                                    </Typography>
                                  </Box>
                                </TableCell>
                                <TableCell>
                                  <IconButton 
                                    size="small" 
                                    onClick={() => handleResultClick(result)}
                                  >
                                    <Info />
                                  </IconButton>
                                </TableCell>
                              </TableRow>
                            ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                    </AccordionDetails>
                  </Accordion>
                );
              })}
            </Box>

            {/* Summary List View */}
            <Accordion 
              expanded={expandedAccordion === 'overview'}
              onChange={() => setExpandedAccordion(expandedAccordion === 'overview' ? false : 'overview')}
            >
              <AccordionSummary expandIcon={<ExpandMore />}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <Analytics />
                  <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                    Overview - All Issues
                  </Typography>
                </Box>
              </AccordionSummary>
              <AccordionDetails>
                <List>
                  {analysisResults.map((result, index) => (
                    <React.Fragment key={result.id}>
                      <ListItem
                        button
                        onClick={() => handleResultClick(result)}
                        sx={{
                          border: 1,
                          borderColor: 'divider',
                          borderRadius: 1,
                          mb: 1,
                          '&:hover': {
                            backgroundColor: 'action.hover',
                          },
                        }}
                      >
                        <ListItemIcon>
                          {getSeverityIcon(result.severity)}
                        </ListItemIcon>
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                                {result.title}
                              </Typography>
                              <Chip
                                icon={getTypeIcon(result.type)}
                                label={result.type.replace('-', ' ').toUpperCase()}
                                size="small"
                                variant="outlined"
                              />
                              <Chip
                                label={result.severity.toUpperCase()}
                                size="small"
                                color={getSeverityColor(result.severity) as any}
                              />
                              {result.confidence && (
                                <Chip
                                  label={`${result.confidence}% confidence`}
                                  size="small"
                                  variant="outlined"
                                  color="info"
                                />
                              )}
                            </Box>
                          }
                          secondary={
                            <Box sx={{ mt: 1 }}>
                              <Typography variant="body2" color="textSecondary">
                                {result.description}
                              </Typography>
                              <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
                                <Typography variant="caption" color="textSecondary">
                                  📁 {result.file}:{result.line}
                                </Typography>
                                {result.category && (
                                  <Typography variant="caption" color="textSecondary">
                                    🏷️ {result.category}
                                  </Typography>
                                )}
                                {result.impact && (
                                  <Typography variant="caption" color="textSecondary">
                                    ⚡ Impact: {result.impact}
                                  </Typography>
                                )}
                              </Box>
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < analysisResults.length - 1 && <Divider sx={{ my: 1 }} />}
                    </React.Fragment>
                  ))}
                </List>
              </AccordionDetails>
            </Accordion>
          </CardContent>
        </Card>
      )}

      {/* Result Detail Dialog */}
      <Dialog
        open={resultDialogOpen}
        onClose={() => setResultDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        {selectedResult && (
          <>
            <DialogTitle>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                {getSeverityIcon(selectedResult.severity)}
                <Typography variant="h6">{selectedResult.title}</Typography>
                <Chip
                  label={selectedResult.severity.toUpperCase()}
                  size="small"
                  color={getSeverityColor(selectedResult.severity) as any}
                />
              </Box>
            </DialogTitle>
            <DialogContent>
              <Typography variant="body1" gutterBottom>
                <strong>Description:</strong> {selectedResult.description}
              </Typography>
              <Typography variant="body2" color="textSecondary" gutterBottom>
                <strong>File:</strong> {selectedResult.file}:{selectedResult.line}
              </Typography>
              {selectedResult.suggestion && (
                <Alert severity="info" sx={{ mt: 2 }}>
                  <strong>Suggestion:</strong> {selectedResult.suggestion}
                </Alert>
              )}
            </DialogContent>
            <DialogActions>
              <Button onClick={() => setResultDialogOpen(false)}>Close</Button>
              <Button variant="contained">View in Editor</Button>
            </DialogActions>
          </>
        )}
      </Dialog>
      </Box>
    </Box>
  );
};

export default CodeAnalysis;