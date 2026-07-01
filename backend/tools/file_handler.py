import os
import mimetypes

def detect_file_type(filepath):
    """
    Detects the file type of the given file path.
    Returns 'pdf', 'csv', 'excel', or 'unknown'.
    """
    _, ext = os.path.splitext(filepath)
    ext = ext.lower()
    
    if ext == '.pdf':
        return 'pdf'
    elif ext == '.csv':
        return 'csv'
    elif ext in ['.xls', '.xlsx']:
        return 'excel'
    elif ext in ['.jpg', '.jpeg', '.png']:
        return 'image'
    
    # Try mimetypes if extension isn't clear
    mime_type, _ = mimetypes.guess_type(filepath)
    if mime_type:
        if mime_type == 'application/pdf':
            return 'pdf'
        elif mime_type == 'text/csv':
            return 'csv'
        elif mime_type in ['application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            return 'excel'
        elif mime_type.startswith('image/'):
            return 'image'
            
    return 'unknown'
