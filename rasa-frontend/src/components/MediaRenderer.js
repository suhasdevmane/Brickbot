// src/components/MediaRenderer.js
import React from 'react';
import { BsDownload } from 'react-icons/bs';

// Updated downloadFile function to open the URL in a new window
function downloadFile(url, filename = 'download') {
  // Open the file in a new tab/window.
  window.open(url, '_blank');
}

// Helper: extract file extension from filename or URL
function getFileExtension(filename) {
  if (!filename) return '';
  const parts = filename.split('.');
  return parts[parts.length - 1].toLowerCase();
}

function MediaRenderer({ media }) {
  if (!media || !media.type) return null;

  // Determine a filename from media.filename or extract from media.url
  const filename = media.filename || (media.url ? media.url.split('/').pop() : 'download');
  const extension = getFileExtension(filename);

  // Render a small download button positioned over the media element
  const renderDownloadButton = () => (
    <button
      onClick={() => downloadFile(media.url, filename)}
      style={{
        position: 'absolute',
        top: '5px',
        right: '5px',
        background: 'rgba(255,255,255,0.7)',
        border: 'none',
        cursor: 'pointer',
        padding: '4px',
        borderRadius: '50%'
      }}
      title="Download"
    >
      <BsDownload size={18} />
    </button>
  );

  // Container style to wrap media and position download button
  const containerStyle = {
    position: 'relative',
    display: 'inline-block',
    marginTop: '10px'
  };

  switch (media.type) {
    case 'text':
      return (
        <div style={containerStyle}>
          <pre style={{ maxWidth: '100%', overflowX: 'auto' }}>
            {media.content}
          </pre>
        </div>
      );

    case 'image':
      return (
        <div style={containerStyle}>
          <img src={media.url} alt="media" style={{ maxWidth: '100%' }} />
          {renderDownloadButton()}
        </div>
      );

    case 'pdf':
      return (
        <div style={containerStyle}>
          <iframe src={media.url} width="100%" height="10%" title="PDF Viewer" />
          {renderDownloadButton()}
        </div>
      );

    case 'chart':
      return (
        <div style={containerStyle}>
          <img src={media.url} alt="chart" style={{ maxWidth: '100%' }} />
          {renderDownloadButton()}
        </div>
      );

    case 'video':
      // For video, support various formats (mp4, flv, mkv, 3gp)
      return (
        <div style={containerStyle}>
          <video controls style={{ maxWidth: '100%' }}>
            <source src={media.url} type={`video/${extension}`} />
            Your browser does not support the video tag.
          </video>
          {renderDownloadButton()}
        </div>
      );

    case 'audio':
      return (
        <div style={containerStyle}>
          <audio controls style={{ maxWidth: '100%' }}>
            <source src={media.url} type={`audio/${extension}`} />
            Your browser does not support the audio element.
          </audio>
          {renderDownloadButton()}
        </div>
      );

    // For non-previewable document types (DOC, XLS, PPT, ZIP, PSD, DXF, SQL, etc.)
    case 'doc':
    case 'docx':
    case 'xls':
    case 'xlsx':
    case 'ppt':
    case 'pptx':
    case 'zip':
    case 'psd':
    case 'dxf':
    case 'sql':
    case 'json':
    case 'xml':
    case 'log':
    case 'txt':
    case 'csv':
    case 'html':
      return (
        <div style={containerStyle}>
          <div style={{
            padding: '0px', // Reduced padding from 20px to 10px
            // border: '1px solid #ccc',
            borderRadius: '1px',
            textAlign: 'center',
            minWidth: '100px',
            maxHeight: '120px', // Added maximum height
            height: '60px',    // Added fixed height
            overflow: 'hidden', // Prevent content from spilling out
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center'
          }}>
            {/* Generic file icon, can be replaced with a specific icon */}
            <div style={{ fontSize: '12px' }}>📄</div> {/* Reduced from 32px */}
            <div style={{ fontSize: '10px', overflow: 'hidden', textOverflow: 'ellipsis' }}>{filename}</div>
            <div style={{ fontSize: '10px', color: '#888' }}>Preview not available</div>
          </div>
          {renderDownloadButton()}
        </div>
      );

    case 'link':
      return (
        <div style={containerStyle}>
          <a href={media.url} target="_blank" rel="noopener noreferrer">
            {media.url}
          </a>
          {renderDownloadButton()}
        </div>
      );

    default:
      return (
        <div style={containerStyle}>
          <div>Unsupported media type: {media.type}</div>
          {renderDownloadButton()}
        </div>
      );
  }
}

export default MediaRenderer;
