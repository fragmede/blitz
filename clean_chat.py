#!/usr/bin/env python3
"""Clean up RTF-to-Markdown conversion artifacts from chat.md"""

import re
import sys

def clean_markdown(content):
    """Remove RTF conversion artifacts from markdown content"""
    
    # First pass: Remove style markers and Apple-converted-space
    content = re.sub(r'\{\.s\d+\}', '', content)
    content = re.sub(r'\{\.Apple-converted-space\}', ' ', content)
    
    # Remove backslash at end of lines (RTF line continuation)
    content = re.sub(r'\\\s*\n', '\n', content)
    
    # Remove empty brackets with any content
    content = re.sub(r'\[\s*\]', '', content)
    
    # Now remove remaining square brackets but keep content
    # This handles simple [content] patterns
    content = re.sub(r'\[([^\[\]]+)\]', r'\1', content)
    
    # Handle nested brackets by running multiple passes
    max_passes = 5
    for _ in range(max_passes):
        new_content = re.sub(r'\[([^\[\]]+)\]', r'\1', content)
        if new_content == content:
            break
        content = new_content
    
    # Clean up escaped characters and backslashes
    content = content.replace(r'\'', "'")
    content = content.replace(r'\"', '"')
    content = content.replace(r'\--', '--')
    content = content.replace(r'\...', '...')
    content = content.replace(r'\#', '#')
    content = content.replace(r'\>', '>')
    content = content.replace(r'\|', '|')
    content = content.replace(r'\(', '(')
    content = content.replace(r'\)', ')')
    content = content.replace(r'\[', '[')
    content = content.replace(r'\]', ']')
    content = content.replace(r'\*', '*')
    content = content.replace(r'\_', '_')
    content = content.replace(r'\`', '`')
    
    # Also handle literal backslash patterns
    content = re.sub(r'\\([#>|\(\)\[\]*_`])', r'\1', content)
    content = re.sub(r'\\\.\.\.', '...', content)
    
    # Clean up multiple consecutive blank lines
    content = re.sub(r'\n{3,}', '\n\n', content)
    
    # Remove trailing whitespace from lines
    lines = content.split('\n')
    lines = [line.rstrip() for line in lines]
    content = '\n'.join(lines)
    
    return content

def main():
    # Read the original file
    with open('chat.md', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Clean it up
    cleaned = clean_markdown(content)
    
    # Write back to the same file
    with open('chat.md', 'w', encoding='utf-8') as f:
        f.write(cleaned)
    
    print("Successfully cleaned chat.md")
    
    # Show a sample of what was done
    print("\nSample of cleaned content (first 500 chars):")
    print("-" * 50)
    print(cleaned[:500])
    print("-" * 50)

if __name__ == '__main__':
    main()