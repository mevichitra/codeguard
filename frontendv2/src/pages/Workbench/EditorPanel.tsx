import React, { useEffect, useRef } from 'react';
import { Paper, Box } from '@mui/material';
import Editor, { type OnMount } from '@monaco-editor/react';

interface EditorPanelProps {
    code: string;
    language: string;
    onChange: (value: string) => void;
    activeLine: number | null;
}

const EditorPanel: React.FC<EditorPanelProps> = ({ code, language, onChange, activeLine }) => {
    const editorRef = useRef<any>(null);
    const decorationsRef = useRef<string[]>([]);

    const handleEditorDidMount: OnMount = (editor, monaco) => {
        editorRef.current = editor;

        // Define custom theme
        monaco.editor.defineTheme('aurora-dark', {
            base: 'vs-dark',
            inherit: true,
            rules: [],
            colors: {
                'editor.background': '#1e293b00', // Transparent
                'editor.lineHighlightBackground': '#ffffff0a',
                'editorLineNumber.foreground': '#64748b',
                'editor.selectionBackground': '#6366f133',
            }
        });

        monaco.editor.setTheme('aurora-dark');
    };

    // Handle line highlighting when activeLine changes
    useEffect(() => {
        if (editorRef.current && activeLine) {
            const editor = editorRef.current;

            // Reveal line
            editor.revealLineInCenter(activeLine);

            // Add decoration
            decorationsRef.current = editor.deltaDecorations(decorationsRef.current, [
                {
                    range: {
                        startLineNumber: activeLine,
                        startColumn: 1,
                        endLineNumber: activeLine,
                        endColumn: 1
                    },
                    options: {
                        isWholeLine: true,
                        className: 'active-line-highlight',
                        glyphMarginClassName: 'active-line-glyph'
                    }
                }
            ]);
        }
    }, [activeLine]);

    return (
        <Paper
            className="glass-panel"
            sx={{
                height: '100%',
                overflow: 'hidden',
                borderRadius: 3,
                display: 'flex',
                flexDirection: 'column',
                bgcolor: 'rgba(15, 23, 42, 0.4)'
            }}
        >
            <Box sx={{ flexGrow: 1, pt: 2 }}>
                <Editor
                    height="100%"
                    defaultLanguage="javascript"
                    language={language}
                    value={code}
                    onChange={(value) => onChange(value || '')}
                    onMount={handleEditorDidMount}
                    options={{
                        minimap: { enabled: false },
                        fontSize: 14,
                        fontFamily: '"JetBrains Mono", monospace',
                        fontLigatures: true,
                        scrollBeyondLastLine: false,
                        smoothScrolling: true,
                        cursorBlinking: 'smooth',
                        cursorSmoothCaretAnimation: 'on',
                        padding: { top: 16, bottom: 16 },
                        lineNumbers: 'on',
                        renderLineHighlight: 'all',
                        roundedSelection: true,
                        automaticLayout: true,
                    }}
                />
            </Box>
        </Paper>
    );
};

export default EditorPanel;
