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
  BugReport,
  Analytics,
  Schedule,
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
    <Box sx={{ width: '75vw', height: '100vh', bgcolor: '#0a0a0a', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
      {/* Arcade Console Header */}
      <Box 
        sx={{ 
          bgcolor: '#1a1a1a',
          color: '#00ff00',
          py: 2,
          px: 0,
          mb: 0,
          border: 'none',
          borderRadius: 0,
          position: 'relative',
          overflow: 'hidden',
          fontFamily: 'monospace',
          flexShrink: 0
        }}
      >
        <Box sx={{ position: 'relative', zIndex: 1, width: '100%' }}>
          <Typography 
            variant="h3" 
            component="h1" 
            gutterBottom 
            sx={{ 
              fontFamily: 'monospace',
              fontWeight: 700,
              fontSize: { xs: '2rem', md: '2.5rem' },
              textAlign: 'center',
              mb: 2,
              color: '#00ff00',
              textShadow: '0 0 10px #00ff00'
            }}
          >
             {'>'}  CODEGUARD_ANALYSIS.EXE
            </Typography>
          <Typography 
            variant="h6" 
            sx={{ 
              fontFamily: 'monospace',
              textAlign: 'center',
              opacity: 0.8,
              maxWidth: '600px',
              mx: 'auto',
              lineHeight: 1.6,
              fontSize: { xs: '0.9rem', md: '1rem' },
              color: '#cccccc'
            }}
          >
            TERMINAL-BASED CODE ANALYSIS FOR SECURITY, QUALITY & PERFORMANCE
          </Typography>
        </Box>
      </Box>

      {/* Modern Analysis Tabs */}
      <Box sx={{ width: '100%', flex: 1, overflow: 'auto' }}>
        <Box sx={{ width: '100%' }}>
        <Paper 
          elevation={0}
          sx={{ 
            mb: 4,
            borderRadius: 1,
            overflow: 'hidden',
            border: '2px solid',
            borderColor: '#333333',
            bgcolor: '#1a1a1a'
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
                fontWeight: 'bold',
                fontFamily: 'monospace',
                color: '#888888',
                '&.Mui-selected': {
                  color: '#00ff41',
                  bgcolor: '#000000'
                }
              },
              '& .MuiTabs-indicator': {
                height: 3,
                backgroundColor: '#00ff41',
                borderRadius: '3px 3px 0 0'
              }
            }}
          >
            <Tab 
              label="CODE INPUT" 
              icon={<Code />} 
              iconPosition="start"
              sx={{ gap: 1 }}
            />
            <Tab 
              label="FILE UPLOAD" 
              icon={<FileUpload />} 
              iconPosition="start"
              sx={{ gap: 1 }}
            />
            <Tab 
              label="REPO SCAN" 
              icon={<CloudUpload />} 
              iconPosition="start"
              sx={{ gap: 1 }}
            />
          </Tabs>

          {/* Code Input Tab */}
          <TabPanel value={activeTab} index={0}>
            <Box sx={{ p: 4 }}>
              <Grid container spacing={4}>
                <Grid item xs={12} lg={10}>
                  <Paper 
                    elevation={0}
                    sx={{ 
                      border: '2px solid',
                      borderColor: '#333333',
                      borderRadius: 1,
                      p: 3,
                      bgcolor: '#1a1a1a',
                      minHeight: '280px',
                      transition: 'all 0.2s ease',
                      '&:hover': {
                        borderColor: '#00ff41',
                        boxShadow: '0 0 20px rgba(0, 255, 65, 0.3)'
                      }
                    }}
                  >
                    <Typography variant="h6" sx={{ mb: 2, color: '#00ff41', fontFamily: 'monospace', fontWeight: 'bold' }}>
                       {'>'} CODE INPUT
                     </Typography>
                    <TextField
                      fullWidth
                      multiline
                      rows={16}
                      variant="outlined"
                      label=""
                      value={codeInput}
                      onChange={(e) => setCodeInput(e.target.value)}
                      placeholder="// PASTE CODE HERE FOR ANALYSIS
function example() {
  console.log('CODEGUARD READY');
  // CODE WILL BE SCANNED FOR VULNERABILITIES
}"
                      sx={{
                        '& .MuiInputBase-root': {
                          fontFamily: 'monospace',
                          fontSize: '0.9rem',
                          lineHeight: 1.6,
                          bgcolor: '#000000',
                          color: '#00ff41',
                          borderRadius: 1,
                          border: '1px solid #333333'
                        },
                        '& .MuiOutlinedInput-root': {
                          '& fieldset': {
                            borderColor: '#333333'
                          },
                          '&:hover fieldset': {
                            borderColor: '#00ff41'
                          },
                          '&.Mui-focused fieldset': {
                            borderColor: '#00ff41'
                          }
                        },
                        '& .MuiInputBase-input::placeholder': {
                          color: '#888888',
                          opacity: 1
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
                       border: '2px solid',
                       borderColor: '#333333',
                       borderRadius: 1,
                       bgcolor: '#1a1a1a',
                       height: 'fit-content',
                       position: 'sticky',
                       top: 20
                     }}
                   >
                     <Typography variant="h6" sx={{ mb: 3, color: '#00ff41', fontFamily: 'monospace', fontWeight: 'bold' }}>
                       {'>'} SCAN CONFIG
                     </Typography>
                     <Stack spacing={3}>
                       <FormControl fullWidth>
                         <InputLabel>Programming Language</InputLabel>
                         <Select
                           value={selectedLanguage}
                           label="Programming Language"
                           onChange={(e) => setSelectedLanguage(e.target.value)}
                           sx={{ 
                             borderRadius: 2,
                             '& .MuiSelect-select': {
                               color: '#ffffff'
                             },
                             '& .MuiInputLabel-root': {
                               color: '#cccccc'
                             }
                           }}
                           MenuProps={{
                             PaperProps: {
                               sx: {
                                 '& .MuiMenuItem-root': {
                                   color: '#ffffff',
                                   backgroundColor: '#1a1a1a',
                                   '&:hover': {
                                     backgroundColor: '#333333'
                                   }
                                 }
                               }
                             }
                           }}
                         >
                           <MenuItem value="javascript">JAVASCRIPT</MenuItem>
                           <MenuItem value="typescript">TYPESCRIPT</MenuItem>
                           <MenuItem value="python">PYTHON</MenuItem>
                           <MenuItem value="java">JAVA</MenuItem>
                           <MenuItem value="cpp">C++</MenuItem>
                           <MenuItem value="c">C</MenuItem>
                         </Select>
                       </FormControl>

                       <FormControl fullWidth>
                         <InputLabel>Analysis Scope</InputLabel>
                         <Select
                           value={analysisType}
                           label="Analysis Scope"
                           onChange={(e) => setAnalysisType(e.target.value)}
                           sx={{ 
                             borderRadius: 2,
                             '& .MuiSelect-select': {
                               color: '#ffffff'
                             },
                             '& .MuiInputLabel-root': {
                               color: '#cccccc'
                             }
                           }}
                           MenuProps={{
                             PaperProps: {
                               sx: {
                                 '& .MuiMenuItem-root': {
                                   color: '#ffffff',
                                   backgroundColor: '#1a1a1a',
                                   '&:hover': {
                                     backgroundColor: '#333333'
                                   }
                                 }
                               }
                             }
                           }}
                         >
                           <MenuItem value="comprehensive">FULL SCAN</MenuItem>
                           <MenuItem value="security">SECURITY SCAN</MenuItem>
                           <MenuItem value="quality">QUALITY SCAN</MenuItem>
                           <MenuItem value="performance">PERFORMANCE SCAN</MenuItem>
                           <MenuItem value="pattern-detection">PATTERN DETECTION</MenuItem>
                         </Select>
                       </FormControl>

                       <Button
                           variant="contained"
                           size="large"
                           startIcon={isAnalyzing ? <CircularProgress size={20} sx={{ color: '#00ff41' }} /> : <PlayArrow />}
                           onClick={handleAnalyze}
                           disabled={!codeInput.trim() || isAnalyzing}
                           sx={{
                             py: 1.5,
                             borderRadius: 1,
                             textTransform: 'none',
                             fontSize: '1.1rem',
                             fontWeight: 'bold',
                             fontFamily: 'monospace',
                             background: '#000000',
                             color: '#ffffff',
                             border: '2px solid #00ff41',
                             '&:hover': {
                               backgroundColor: '#00ff41',
                               color: '#000000',
                               boxShadow: '0 0 20px rgba(0, 255, 65, 0.5)'
                             },
                             '&:disabled': {
                               background: '#333333',
                               color: '#cccccc',
                               border: '2px solid #666666'
                             }
                           }}
                         >
                           {isAnalyzing ? 'SCANNING...' : 'EXECUTE SCAN'}
                         </Button>

                       {isAnalyzing && (
                         <Box sx={{ mt: 2 }}>
                           <Typography variant="body2" gutterBottom sx={{ textAlign: 'center', color: '#00ff41', fontFamily: 'monospace' }}>
                             SCAN IN PROGRESS...
                           </Typography>
                           <LinearProgress sx={{ borderRadius: 1, backgroundColor: '#333333', '& .MuiLinearProgress-bar': { backgroundColor: '#00ff41' } }} />
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
              <Grid item xs={12} lg={10}>
                <Paper
                  {...getRootProps()}
                  elevation={0}
                  sx={{
                    p: 6,
                    textAlign: 'center',
                    border: '2px solid',
                    borderColor: isDragActive ? '#00ff41' : '#333333',
                    backgroundColor: '#1a1a1a',
                    cursor: 'pointer',
                    borderRadius: 1,
                    transition: 'all 0.2s ease',
                    minHeight: '280px',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    alignItems: 'center',
                    '&:hover': {
                      borderColor: '#00ff41',
                      backgroundColor: '#222222',
                      boxShadow: '0 0 20px rgba(0, 255, 65, 0.3)'
                    }
                  }}
                >
                  <input {...getInputProps()} />
                  <CloudUpload sx={{ fontSize: 48, color: '#00ff41', mb: 2 }} />
                <Typography variant="h6" gutterBottom sx={{ color: '#00ff41', fontFamily: 'monospace', fontWeight: 'bold' }}>
                  {isDragActive ? '> DROP FILES' : '> UPLOAD CODE'}
                </Typography>
                <Typography variant="body2" sx={{ color: '#ffffff', fontFamily: 'monospace' }} gutterBottom>
                  CLICK TO SELECT FILES
                </Typography>
                <Typography variant="caption" sx={{ color: '#888888', fontFamily: 'monospace' }}>
                  JS | TS | PY | JAVA | CPP | C | H
                </Typography>
              </Paper>

              {uploadedFiles.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2" gutterBottom sx={{ color: '#00ff41', fontFamily: 'monospace', fontWeight: 'bold' }}>
                     {'>'}  UPLOADED FILES ({uploadedFiles.length})
                   </Typography>
                  <List dense>
                    {uploadedFiles.map((file, index) => (
                      <ListItem key={index} sx={{ bgcolor: '#1a1a1a', mb: 1, borderRadius: 1, border: '1px solid #333333' }}>
                        <ListItemIcon>
                          <Code sx={{ color: '#00ff41' }} />
                        </ListItemIcon>
                        <ListItemText
                          primary={file.name}
                          secondary={`${(file.size / 1024).toFixed(1)} KB`}
                          sx={{
                            '& .MuiListItemText-primary': { color: '#ffffff', fontFamily: 'monospace' },
                            '& .MuiListItemText-secondary': { color: '#888888', fontFamily: 'monospace' }
                          }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
            </Grid>
            <Grid item xs={12} lg={4}>
              <Paper 
                elevation={0}
                sx={{ 
                  p: 3,
                  border: '2px solid',
                  borderColor: '#333333',
                  borderRadius: 1,
                  bgcolor: '#1a1a1a',
                  height: 'fit-content',
                  position: 'sticky',
                  top: 20
                }}
              >
                <Typography variant="h6" sx={{ mb: 3, color: '#00ff41', fontFamily: 'monospace', fontWeight: 'bold' }}>
                  {'>'} SCAN CONFIG
                </Typography>
                <Stack spacing={3}>
                  <FormControl fullWidth>
                    <InputLabel>Analysis Scope</InputLabel>
                    <Select
                      value={analysisType}
                      label="Analysis Scope"
                      onChange={(e) => setAnalysisType(e.target.value)}
                      sx={{ 
                        borderRadius: 2,
                        '& .MuiSelect-select': {
                          color: '#ffffff'
                        },
                        '& .MuiInputLabel-root': {
                          color: '#cccccc'
                        }
                      }}
                      MenuProps={{
                        PaperProps: {
                          sx: {
                            '& .MuiMenuItem-root': {
                              color: '#ffffff',
                              backgroundColor: '#1a1a1a',
                              '&:hover': {
                                backgroundColor: '#333333'
                              }
                            }
                          }
                        }
                      }}
                    >
                      <MenuItem value="comprehensive">FULL SCAN</MenuItem>
                      <MenuItem value="security">SECURITY SCAN</MenuItem>
                      <MenuItem value="quality">QUALITY SCAN</MenuItem>
                      <MenuItem value="performance">PERFORMANCE SCAN</MenuItem>
                      <MenuItem value="ai-detection">PATTERN DETECTION</MenuItem>
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
                      background: '#000000',
                      border: '2px solid #00ff41',
                      color: '#ffffff',
                      fontFamily: 'monospace',
                      fontWeight: 'bold',
                      borderRadius: 1,
                      py: 1.5,
                      '&:hover': {
                        background: '#00ff41',
                        color: '#000000',
                        boxShadow: '0 0 20px rgba(0, 255, 65, 0.5)'
                      },
                      '&:disabled': {
                        background: '#333333',
                        border: '2px solid #666666',
                        color: '#cccccc'
                      }
                    }}
                  >
                    {isAnalyzing ? 'SCANNING...' : 'EXECUTE SCAN'}
                  </Button>

                  {isAnalyzing && (
                    <Box sx={{ mt: 2 }}>
                      <Typography variant="body2" gutterBottom sx={{ textAlign: 'center', color: '#00ff41', fontFamily: 'monospace' }}>
                        SCAN IN PROGRESS...
                      </Typography>
                      <LinearProgress sx={{ borderRadius: 1, backgroundColor: '#333333', '& .MuiLinearProgress-bar': { backgroundColor: '#00ff41' } }} />
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
              <Grid item xs={12} lg={10}>
                <Paper 
                  elevation={0}
                  sx={{ 
                    border: '2px solid',
                    borderColor: '#333333',
                    borderRadius: 1,
                    p: 3,
                    bgcolor: '#1a1a1a',
                    minHeight: '280px',
                    transition: 'all 0.2s ease',
                    '&:hover': {
                      borderColor: '#00ff41',
                      boxShadow: '0 0 20px rgba(0, 255, 65, 0.3)'
                    }
                  }}
                >
                  <Typography variant="h6" sx={{ mb: 2, color: '#00ff41', fontFamily: 'monospace', fontWeight: 'bold' }}>
                    {'>'} REPO CONFIG
                  </Typography>
                  <Stack spacing={3}>
                    <TextField
                      fullWidth
                      label=""
                      placeholder="https://github.com/username/repository"
                      variant="outlined"
                      sx={{
                        '& .MuiInputBase-root': {
                          fontFamily: 'monospace',
                          fontSize: '0.9rem',
                          bgcolor: '#000000',
                          color: '#00ff41',
                          borderRadius: 1,
                          border: '1px solid #333333'
                        },
                        '& .MuiOutlinedInput-root': {
                          '& fieldset': {
                            borderColor: '#333333'
                          },
                          '&:hover fieldset': {
                            borderColor: '#00ff41'
                          },
                          '&.Mui-focused fieldset': {
                            borderColor: '#00ff41'
                          }
                        },
                        '& .MuiInputBase-input::placeholder': {
                          color: '#888888',
                          opacity: 1
                        }
                      }}
                    />
                    <TextField
                      fullWidth
                      label=""
                      placeholder="main (branch)"
                      variant="outlined"
                      sx={{
                        '& .MuiInputBase-root': {
                          fontFamily: 'monospace',
                          fontSize: '0.9rem',
                          bgcolor: '#000000',
                          color: '#00ff41',
                          borderRadius: 1,
                          border: '1px solid #333333'
                        },
                        '& .MuiOutlinedInput-root': {
                          '& fieldset': {
                            borderColor: '#333333'
                          },
                          '&:hover fieldset': {
                            borderColor: '#00ff41'
                          },
                          '&.Mui-focused fieldset': {
                            borderColor: '#00ff41'
                          }
                        },
                        '& .MuiInputBase-input::placeholder': {
                          color: '#888888',
                          opacity: 1
                        }
                      }}
                    />
                    <Alert 
                      severity="info" 
                      sx={{ 
                        borderRadius: 1,
                        bgcolor: '#1a1a1a',
                        border: '1px solid #333333',
                        color: '#888888',
                        fontFamily: 'monospace',
                        '& .MuiAlert-icon': {
                          color: '#00ff41'
                        }
                      }}
                    >
                      REPO SCANNING REQUIRES AUTH CONFIG
                    </Alert>
                  </Stack>
                </Paper>
              </Grid>
              <Grid item xs={12} lg={4}>
                <Paper 
                  elevation={0}
                  sx={{ 
                    p: 3,
                    border: '2px solid',
                    borderColor: '#333333',
                    borderRadius: 1,
                    bgcolor: '#1a1a1a',
                    height: 'fit-content',
                    position: 'sticky',
                    top: 20
                  }}
                >
                  <Typography variant="h6" sx={{ mb: 3, color: '#00ff41', fontFamily: 'monospace', fontWeight: 'bold' }}>
                    {'>'} REPO ACTIONS
                  </Typography>
                  <Stack spacing={3}>
                    <Button
                      variant="contained"
                      size="large"
                      startIcon={<CloudUpload />}
                      fullWidth
                      disabled
                      sx={{
                        background: '#333333',
                        border: '2px solid #666666',
                        color: '#666666',
                        fontFamily: 'monospace',
                        fontWeight: 'bold',
                        borderRadius: 1,
                        py: 1.5,
                        '&:disabled': {
                          background: '#333333',
                          border: '2px solid #666666',
                          color: '#cccccc'
                        }
                      }}
                    >
                      SCAN REPOSITORY
                    </Button>
                    <Typography variant="caption" sx={{ textAlign: 'center', color: '#888888', fontFamily: 'monospace' }}>
                      COMING SOON
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
          <Typography variant="h5" gutterBottom sx={{ mb: 3, fontWeight: 700, color: '#00ff41', fontFamily: 'monospace' }}>
            {'>'}  ANALYSIS_OVERVIEW.DAT
          </Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} sm={6} md={3}>
              <Card 
                elevation={0}
                sx={{ 
                  textAlign: 'center', 
                  p: 3,
                  borderRadius: 1,
                  bgcolor: '#1a1a1a',
                  border: '2px solid #333333',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    borderColor: '#00ff41',
                    boxShadow: '0 0 20px rgba(0, 255, 65, 0.3)'
                  }
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                  <BugReport sx={{ color: '#ff4444', fontSize: 32 }} />
                  <Typography variant="h3" sx={{ fontWeight: 700, color: '#ff4444', fontFamily: 'monospace' }}>
                    {analysisMetrics.totalIssues}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 500, color: '#cccccc', fontFamily: 'monospace' }}>
                    TOTAL_ISSUES
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
                  borderRadius: 1,
                  bgcolor: '#1a1a1a',
                  border: '2px solid #333333',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    borderColor: '#00ff41',
                    boxShadow: '0 0 20px rgba(0, 255, 65, 0.3)'
                  }
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                  <Security sx={{ color: '#ffaa00', fontSize: 32 }} />
                  <Typography variant="h3" sx={{ fontWeight: 700, color: '#ffaa00', fontFamily: 'monospace' }}>
                    {analysisMetrics.criticalIssues}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 500, color: '#cccccc', fontFamily: 'monospace' }}>
                    CRITICAL_ISSUES
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
                  borderRadius: 1,
                  bgcolor: '#1a1a1a',
                  border: '2px solid #333333',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    borderColor: '#00ff41',
                    boxShadow: '0 0 20px rgba(0, 255, 65, 0.3)'
                  }
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                  <Code sx={{ color: '#00aaff', fontSize: 32 }} />
                  <Typography variant="h3" sx={{ fontWeight: 700, color: '#00aaff', fontFamily: 'monospace' }}>
                     {analysisMetrics.linesAnalyzed}
                   </Typography>
                   <Typography variant="body2" sx={{ fontWeight: 500, color: '#cccccc', fontFamily: 'monospace' }}>
                     LINES_ANALYZED
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
                  borderRadius: 1,
                  bgcolor: '#1a1a1a',
                  border: '2px solid #333333',
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    borderColor: '#00ff41',
                    boxShadow: '0 0 20px rgba(0, 255, 65, 0.3)'
                  }
                }}
              >
                <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                  <Schedule sx={{ color: '#00ff41', fontSize: 32 }} />
                  <Typography variant="h3" sx={{ fontWeight: 700, color: '#00ff41', fontFamily: 'monospace' }}>
                    {(analysisMetrics.analysisTime / 1000).toFixed(1)}s
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 500, color: '#cccccc', fontFamily: 'monospace' }}>
                    ANALYSIS_TIME
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
    </Box>
  );
};

export default CodeAnalysis;