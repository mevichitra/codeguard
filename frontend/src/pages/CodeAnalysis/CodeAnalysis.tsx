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
  Error,
  Warning,
  Info,
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
    setIsAnalyzing(true);
    
    // Simulate analysis
    setTimeout(() => {
      setAnalysisResults(mockAnalysisResults);
      setShowResults(true);
      setIsAnalyzing(false);
    }, 3000);
  };

  const handleResultClick = (result: AnalysisResult) => {
    setSelectedResult(result);
    setResultDialogOpen(true);
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high':
        return <Error color="error" />;
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
    <Box sx={{ width: '100%' }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 700 }}>
          Code Analysis
        </Typography>
        <Typography variant="body1" color="textSecondary">
          Analyze your code for security vulnerabilities, quality issues, performance bottlenecks, and AI-generated patterns
        </Typography>
      </Box>

      {/* Analysis Tabs */}
      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          aria-label="analysis tabs"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Code Input" icon={<Code />} />
          <Tab label="File Upload" icon={<FileUpload />} />
          <Tab label="Repository Scan" icon={<CloudUpload />} />
        </Tabs>

        {/* Code Input Tab */}
        <TabPanel value={activeTab} index={0}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <TextField
                fullWidth
                multiline
                rows={15}
                variant="outlined"
                label="Paste your code here"
                value={codeInput}
                onChange={(e) => setCodeInput(e.target.value)}
                placeholder="// Paste your code here for analysis...
function example() {
  // Your code
}"
                sx={{
                  '& .MuiInputBase-root': {
                    fontFamily: 'Monaco, Consolas, "Courier New", monospace',
                    fontSize: '0.875rem',
                  },
                }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <FormControl fullWidth>
                  <InputLabel>Language</InputLabel>
                  <Select
                    value={selectedLanguage}
                    label="Language"
                    onChange={(e) => setSelectedLanguage(e.target.value)}
                  >
                    <MenuItem value="javascript">JavaScript</MenuItem>
                    <MenuItem value="typescript">TypeScript</MenuItem>
                    <MenuItem value="python">Python</MenuItem>
                    <MenuItem value="java">Java</MenuItem>
                    <MenuItem value="cpp">C++</MenuItem>
                    <MenuItem value="c">C</MenuItem>
                  </Select>
                </FormControl>

                <FormControl fullWidth>
                  <InputLabel>Analysis Type</InputLabel>
                  <Select
                    value={analysisType}
                    label="Analysis Type"
                    onChange={(e) => setAnalysisType(e.target.value)}
                  >
                    <MenuItem value="comprehensive">Comprehensive</MenuItem>
                    <MenuItem value="security">Security Only</MenuItem>
                    <MenuItem value="quality">Quality Only</MenuItem>
                    <MenuItem value="performance">Performance Only</MenuItem>
                    <MenuItem value="ai-detection">AI Detection Only</MenuItem>
                  </Select>
                </FormControl>

                <Button
                  variant="contained"
                  size="large"
                  startIcon={isAnalyzing ? <Stop /> : <PlayArrow />}
                  onClick={handleAnalyze}
                  disabled={!codeInput.trim() || isAnalyzing}
                  fullWidth
                >
                  {isAnalyzing ? 'Analyzing...' : 'Analyze Code'}
                </Button>

                {isAnalyzing && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="body2" gutterBottom>
                      Analysis in progress...
                    </Typography>
                    <LinearProgress />
                  </Box>
                )}
              </Box>
            </Grid>
          </Grid>
        </TabPanel>

        {/* File Upload Tab */}
        <TabPanel value={activeTab} index={1}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Paper
                {...getRootProps()}
                sx={{
                  p: 4,
                  textAlign: 'center',
                  border: '2px dashed',
                  borderColor: isDragActive ? 'primary.main' : 'grey.300',
                  backgroundColor: isDragActive ? 'action.hover' : 'background.paper',
                  cursor: 'pointer',
                  transition: 'all 0.2s ease',
                }}
              >
                <input {...getInputProps()} />
                <CloudUpload sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
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
            <Grid item xs={12} md={6}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <FormControl fullWidth>
                  <InputLabel>Analysis Type</InputLabel>
                  <Select
                    value={analysisType}
                    label="Analysis Type"
                    onChange={(e) => setAnalysisType(e.target.value)}
                  >
                    <MenuItem value="comprehensive">Comprehensive</MenuItem>
                    <MenuItem value="security">Security Only</MenuItem>
                    <MenuItem value="quality">Quality Only</MenuItem>
                    <MenuItem value="performance">Performance Only</MenuItem>
                    <MenuItem value="ai-detection">AI Detection Only</MenuItem>
                  </Select>
                </FormControl>

                <Button
                  variant="contained"
                  size="large"
                  startIcon={<PlayArrow />}
                  onClick={handleAnalyze}
                  disabled={uploadedFiles.length === 0 || isAnalyzing}
                  fullWidth
                >
                  Analyze Files
                </Button>
              </Box>
            </Grid>
          </Grid>
        </TabPanel>

        {/* Repository Scan Tab */}
        <TabPanel value={activeTab} index={2}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={8}>
              <TextField
                fullWidth
                label="Repository URL"
                placeholder="https://github.com/username/repository"
                variant="outlined"
                sx={{ mb: 2 }}
              />
              <TextField
                fullWidth
                label="Branch (optional)"
                placeholder="main"
                variant="outlined"
                sx={{ mb: 2 }}
              />
              <Alert severity="info" sx={{ mb: 2 }}>
                Repository scanning requires authentication. Configure your Git credentials in Settings.
              </Alert>
            </Grid>
            <Grid item xs={12} md={4}>
              <Button
                variant="contained"
                size="large"
                startIcon={<CloudUpload />}
                fullWidth
                disabled
              >
                Scan Repository
              </Button>
              <Typography variant="caption" color="textSecondary" sx={{ mt: 1, display: 'block' }}>
                Coming soon in next release
              </Typography>
            </Grid>
          </Grid>
        </TabPanel>
      </Paper>

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
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
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
                        </Box>
                      }
                      secondary={
                        <Box sx={{ mt: 1 }}>
                          <Typography variant="body2" color="textSecondary">
                            {result.description}
                          </Typography>
                          <Typography variant="caption" color="textSecondary">
                            {result.file}:{result.line}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItem>
                  {index < analysisResults.length - 1 && <Divider sx={{ my: 1 }} />}
                </React.Fragment>
              ))}
            </List>
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
  );
};

export default CodeAnalysis;