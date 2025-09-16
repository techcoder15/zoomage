import React, { useState, useEffect, useRef, useCallback } from 'react';
import './App.css';
import OpenSeadragon from 'openseadragon';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

function App() {
  const [searchQuery, setSearchQuery] = useState('');
  const [images, setImages] = useState([]);
  const [selectedImage, setSelectedImage] = useState(null);
  const [labels, setLabels] = useState([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [aiAnalysis, setAiAnalysis] = useState('');
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [patterns, setPatterns] = useState('');
  const [showPatterns, setShowPatterns] = useState(false);
  const [isAddingLabel, setIsAddingLabel] = useState(false);
  const [newLabel, setNewLabel] = useState({ 
    label: '', 
    description: '', 
    category: '', 
    x: 0.5, 
    y: 0.5, 
    width: 0.0, 
    height: 0.0 
  });
  
  const viewerRef = useRef(null);
  const osdViewerRef = useRef(null);

  // Search NASA images
  const searchImages = async () => {
    if (!searchQuery.trim()) return;
    
    setIsSearching(true);
    try {
      const response = await axios.post(`${API}/search`, {
        query: searchQuery,
        media_type: 'image'
      });
      setImages(response.data);
    } catch (error) {
      console.error('Error searching images:', error);
      alert('Error searching images');
    } finally {
      setIsSearching(false);
    }
  };

  // Load saved images on startup
  useEffect(() => {
    const loadSavedImages = async () => {
      try {
        const response = await axios.get(`${API}/images`);
        if (response.data.length > 0) {
          setImages(response.data);
        }
      } catch (error) {
        console.error('Error loading saved images:', error);
      }
    };
    loadSavedImages();
  }, []);

  // Initialize OpenSeadragon viewer
  const initializeViewer = useCallback((imageUrl) => {
    if (osdViewerRef.current) {
      osdViewerRef.current.destroy();
    }

    if (viewerRef.current && imageUrl) {
      osdViewerRef.current = OpenSeadragon({
        element: viewerRef.current,
        prefixUrl: 'https://openseadragon.github.io/openseadragon/images/',
        tileSources: {
          type: 'image',
          url: imageUrl,
          buildPyramid: false
        },
        showNavigationControl: true,
        showZoomControl: true,
        showHomeControl: true,
        showFullPageControl: true,
        showRotationControl: true,
        gestureSettingsMouse: {
          clickToZoom: false,
          dblClickToZoom: true,
          dragToPan: true,
          scrollToZoom: true,
          pinchToZoom: true
        },
        zoomInButton: 'zoom-in',
        zoomOutButton: 'zoom-out',
        homeButton: 'home',
        fullPageButton: 'full-page',
        rotateLeftButton: 'rotate-left',
        rotateRightButton: 'rotate-right',
        animationTime: 0.5,
        blendTime: 0.1,
        constrainDuringPan: false,
        maxZoomPixelRatio: 10,
        minZoomLevel: 0.1,
        visibilityRatio: 0.1,
        springStiffness: 6.5
      });

      // Add click handler for adding labels
      osdViewerRef.current.addHandler('canvas-click', (event) => {
        if (isAddingLabel) {
          const viewportPoint = osdViewerRef.current.viewport.pointFromPixel(event.position);
          setNewLabel(prev => ({
            ...prev,
            x: viewportPoint.x,
            y: viewportPoint.y
          }));
        }
      });

      // Load existing labels
      loadLabels(selectedImage.id);
    }
  }, [selectedImage, isAddingLabel, newLabel]);

  // Load labels for an image
  const loadLabels = async (imageId) => {
    try {
      const response = await axios.get(`${API}/images/${imageId}/labels`);
      setLabels(response.data);
    } catch (error) {
      console.error('Error loading labels:', error);
    }
  };

  // Select image for viewing
  const selectImage = (image) => {
    setSelectedImage(image);
    setAiAnalysis('');
    setShowAnalysis(false);
  };

  // Initialize viewer when image is selected
  useEffect(() => {
    if (selectedImage) {
      initializeViewer(selectedImage.url);
    }
  }, [selectedImage, initializeViewer]);

  // AI Analysis
  const analyzeWithAI = async (analysisType = 'general') => {
    if (!selectedImage) return;
    
    setIsAnalyzing(true);
    try {
      const response = await axios.post(`${API}/analyze`, {
        image_url: selectedImage.url,
        analysis_type: analysisType
      });
      setAiAnalysis(response.data.analysis);
      setShowAnalysis(true);
    } catch (error) {
      console.error('Error analyzing image:', error);
      alert('Error analyzing image');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Add label
  const addLabel = async () => {
    if (!selectedImage || !newLabel.label.trim()) return;
    
    try {
      const label = {
        ...newLabel,
        // Ensure numeric values
        x: Number(newLabel.x) || 0.5,
        y: Number(newLabel.y) || 0.5,
        width: Number(newLabel.width) || 0.0,
        height: Number(newLabel.height) || 0.0
      };
      
      console.log('Submitting label:', label); // Debug log
      
      await axios.post(`${API}/images/${selectedImage.id}/labels`, label);
      loadLabels(selectedImage.id);
      setNewLabel({ 
        label: '', 
        description: '', 
        category: '', 
        x: 0.5, 
        y: 0.5, 
        width: 0.0, 
        height: 0.0 
      });
      setIsAddingLabel(false);
    } catch (error) {
      console.error('Error adding label:', error);
      console.error('Label data that failed:', newLabel); // Debug log
      alert('Error adding label: ' + (error.response?.data?.detail || error.message));
    }
  };

  // Delete label
  const deleteLabel = async (labelId) => {
    try {
      await axios.delete(`${API}/images/${selectedImage.id}/labels/${labelId}`);
      loadLabels(selectedImage.id);
    } catch (error) {
      console.error('Error deleting label:', error);
    }
  };

  // Discover patterns
  const discoverPatterns = async () => {
    try {
      const response = await axios.get(`${API}/discover`);
      setPatterns(response.data.patterns);
      setShowPatterns(true);
    } catch (error) {
      console.error('Error discovering patterns:', error);
      alert('Error discovering patterns');
    }
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 p-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-3xl font-bold text-blue-400">
            🔭 Zoomage - NASA Image Explorer
          </h1>
          <p className="text-gray-300">Embiggen Your Eyes!</p>
        </div>
      </header>

      <div className="flex h-screen">
        {/* Sidebar */}
        <div className="w-80 bg-gray-800 border-r border-gray-700 p-4 overflow-y-auto">
          {/* Search Section */}
          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-3 text-blue-300">Search NASA Images</h2>
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search space images..."
                className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                onKeyPress={(e) => e.key === 'Enter' && searchImages()}
              />
              <button
                onClick={searchImages}
                disabled={isSearching}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors"
              >
                {isSearching ? '🔍' : '🚀'}
              </button>
            </div>
          </div>

          {/* Pattern Discovery */}
          <div className="mb-6">
            <button
              onClick={discoverPatterns}
              className="w-full px-4 py-2 bg-purple-600 hover:bg-purple-700 rounded-lg transition-colors"
            >
              🧠 Discover Patterns
            </button>
          </div>

          {/* Image Gallery */}
          <div className="space-y-3">
            <h3 className="text-lg font-semibold text-green-300">Images ({images.length})</h3>
            {images.map((image) => (
              <div
                key={image.id}
                onClick={() => selectImage(image)}
                className={`cursor-pointer p-3 rounded-lg border transition-all ${
                  selectedImage?.id === image.id
                    ? 'border-blue-500 bg-blue-900/20'
                    : 'border-gray-600 bg-gray-700 hover:bg-gray-600'
                }`}
              >
                {image.thumbnail_url && (
                  <img
                    src={image.thumbnail_url}
                    alt={image.title}
                    className="w-full h-32 object-cover rounded mb-2"
                  />
                )}
                <h4 className="font-medium truncate">{image.title}</h4>
                <p className="text-sm text-gray-400 line-clamp-2">
                  {image.description?.substring(0, 100)}...
                </p>
                {image.labels.length > 0 && (
                  <div className="mt-2">
                    <span className="text-xs bg-green-600 px-2 py-1 rounded">
                      {image.labels.length} labels
                    </span>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {selectedImage ? (
            <>
              {/* Image Controls */}
              <div className="bg-gray-800 border-b border-gray-700 p-4">
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-xl font-semibold text-blue-300 truncate">
                    {selectedImage.title}
                  </h2>
                  <div className="flex gap-2">
                    <button
                      onClick={() => analyzeWithAI('general')}
                      disabled={isAnalyzing}
                      className="px-3 py-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded text-sm transition-colors"
                    >
                      {isAnalyzing ? '🤖...' : '🤖 AI Analyze'}
                    </button>
                    <button
                      onClick={() => analyzeWithAI('features')}
                      disabled={isAnalyzing}
                      className="px-3 py-1 bg-yellow-600 hover:bg-yellow-700 disabled:opacity-50 rounded text-sm transition-colors"
                    >
                      🔍 Features
                    </button>
                    <button
                      onClick={() => analyzeWithAI('patterns')}
                      disabled={isAnalyzing}
                      className="px-3 py-1 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 rounded text-sm transition-colors"
                    >
                      🧩 Patterns
                    </button>
                    <button
                      onClick={() => setIsAddingLabel(!isAddingLabel)}
                      className={`px-3 py-1 rounded text-sm transition-colors ${
                        isAddingLabel
                          ? 'bg-red-600 hover:bg-red-700'
                          : 'bg-blue-600 hover:bg-blue-700'
                      }`}
                    >
                      {isAddingLabel ? '❌ Cancel' : '🏷️ Add Label'}
                    </button>
                  </div>
                </div>
                
                {/* Label Input */}
                {isAddingLabel && (
                  <div className="mt-3 p-3 bg-gray-700 rounded-lg">
                    <div className="grid grid-cols-3 gap-2 mb-2">
                      <input
                        type="text"
                        placeholder="Label name"
                        value={newLabel.label}
                        onChange={(e) => setNewLabel({...newLabel, label: e.target.value})}
                        className="px-2 py-1 bg-gray-600 border border-gray-500 rounded text-sm"
                      />
                      <input
                        type="text"
                        placeholder="Category"
                        value={newLabel.category}
                        onChange={(e) => setNewLabel({...newLabel, category: e.target.value})}
                        className="px-2 py-1 bg-gray-600 border border-gray-500 rounded text-sm"
                      />
                      <button
                        onClick={addLabel}
                        disabled={!newLabel.label.trim()}
                        className="px-2 py-1 bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded text-sm"
                      >
                        Add
                      </button>
                    </div>
                    <input
                      type="text"
                      placeholder="Description"
                      value={newLabel.description}
                      onChange={(e) => setNewLabel({...newLabel, description: e.target.value})}
                      className="w-full px-2 py-1 bg-gray-600 border border-gray-500 rounded text-sm"
                    />
                    <p className="text-xs text-gray-400 mt-1">Click on the image to place the label</p>
                  </div>
                )}
              </div>

              {/* OpenSeadragon Viewer */}
              <div className="flex-1 relative">
                <div ref={viewerRef} className="w-full h-full" />
                
                {/* Navigation Controls */}
                <div className="absolute top-4 right-4 flex flex-col gap-2">
                  <button id="zoom-in" className="w-10 h-10 bg-gray-800/80 hover:bg-gray-700 rounded-lg flex items-center justify-center text-white">+</button>
                  <button id="zoom-out" className="w-10 h-10 bg-gray-800/80 hover:bg-gray-700 rounded-lg flex items-center justify-center text-white">-</button>
                  <button id="home" className="w-10 h-10 bg-gray-800/80 hover:bg-gray-700 rounded-lg flex items-center justify-center text-white">🏠</button>
                  <button id="full-page" className="w-10 h-10 bg-gray-800/80 hover:bg-gray-700 rounded-lg flex items-center justify-center text-white">⛶</button>
                  <button id="rotate-left" className="w-10 h-10 bg-gray-800/80 hover:bg-gray-700 rounded-lg flex items-center justify-center text-white">↺</button>
                  <button id="rotate-right" className="w-10 h-10 bg-gray-800/80 hover:bg-gray-700 rounded-lg flex items-center justify-center text-white">↻</button>
                </div>

                {/* Labels Panel */}
                {labels.length > 0 && (
                  <div className="absolute bottom-4 left-4 max-w-xs bg-gray-800/90 rounded-lg p-3 max-h-48 overflow-y-auto">
                    <h4 className="font-semibold mb-2 text-blue-300">Labels ({labels.length})</h4>
                    <div className="space-y-2">
                      {labels.map((label) => (
                        <div key={label.id} className="text-sm bg-gray-700 p-2 rounded flex justify-between items-start">
                          <div>
                            <div className="font-medium">{label.label}</div>
                            {label.category && (
                              <div className="text-xs text-gray-400">{label.category}</div>
                            )}
                            {label.description && (
                              <div className="text-xs text-gray-300 mt-1">{label.description}</div>
                            )}
                          </div>
                          <button
                            onClick={() => deleteLabel(label.id)}
                            className="text-red-400 hover:text-red-300 ml-2"
                          >
                            ❌
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="text-6xl mb-4">🔭</div>
                <h2 className="text-2xl font-semibold mb-2">Welcome to Zoomage</h2>
                <p className="text-gray-400 mb-4">
                  Search for NASA images and explore them with ultra-clarity zoom
                </p>
                <p className="text-sm text-gray-500">
                  Select an image from the sidebar to start exploring
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* AI Analysis Modal */}
      {showAnalysis && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg p-6 max-w-2xl w-full max-h-96 overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold text-blue-300">🤖 AI Analysis</h3>
              <button
                onClick={() => setShowAnalysis(false)}
                className="text-gray-400 hover:text-white"
              >
                ❌
              </button>
            </div>
            <div className="text-gray-200 whitespace-pre-wrap">{aiAnalysis}</div>
          </div>
        </div>
      )}

      {/* Pattern Discovery Modal */}
      {showPatterns && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg p-6 max-w-4xl w-full max-h-96 overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold text-purple-300">🧠 Pattern Discoveries</h3>
              <button
                onClick={() => setShowPatterns(false)}
                className="text-gray-400 hover:text-white"
              >
                ❌
              </button>
            </div>
            <div className="text-gray-200 whitespace-pre-wrap">{patterns}</div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;