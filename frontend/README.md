# FitAI Frontend - PWA Dashboard

Advanced Progressive Web App for IoT fitness telemetry and CNS recovery tracking.

## Features

### Core Functionality
- **Live Telemetry**: Real-time activity monitoring with velocity, heart rate, and kinematic scoring
- **CNS Recovery**: Predictive readiness forecasting with 30-day trend analysis
- **Session History**: Complete workout session database with performance metrics
- **Data Export**: CSV export of raw telemetry data

### PWA Capabilities
- **Offline Support**: Service worker caches critical assets and API responses
- **Installable**: Add to home screen on mobile devices
- **Background Sync**: Automatically syncs recovery data when back online
- **Push Notifications**: Framework ready for future notification features
- **Responsive Design**: Optimized for desktop, tablet, and mobile

## File Structure

```
frontend/
├── index.html          # Main PWA application
├── manifest.json       # PWA manifest for installation
├── sw.js              # Service worker for offline functionality
└── README.md          # This file
```

## PWA Setup

### Service Worker
- Caches static assets (HTML, CSS, JS libraries)
- Implements network-first strategy for API calls
- Provides offline fallbacks for critical data
- Handles background sync for recovery metrics

### Manifest
- Defines app metadata and icons
- Configures display mode (standalone)
- Sets theme colors and orientation

### Offline Features
- Graceful degradation when network unavailable
- Cached data display with staleness indicators
- Recovery data queuing for later sync
- Visual offline/online status indicators

## Development

### Local Development
```bash
# Serve with a local HTTP server that supports PWA features
python -m http.server 8001
# or
npx serve . -p 8001
```

### Testing PWA Features
1. **Service Worker**: Check DevTools → Application → Service Workers
2. **Manifest**: Check DevTools → Application → Manifest
3. **Offline**: Use DevTools → Network → Offline checkbox
4. **Install**: Use DevTools → Application → Install app

### Browser Support
- Chrome/Edge: Full PWA support
- Firefox: Basic PWA support (no background sync)
- Safari: Limited PWA support
- Mobile browsers: Full support on modern Android/iOS

## Future Enhancements

### Planned Features
- Push notifications for recovery milestones
- Advanced caching strategies
- Data synchronization conflicts resolution
- Progressive loading of heavy charts
- Voice commands for hands-free operation

### Performance Optimizations
- Code splitting and lazy loading
- Image optimization and WebP support
- Bundle analysis and tree shaking
- Critical CSS inlining
- Service worker precaching improvements

### Mobile Enhancements
- Touch gesture support
- Native device sensor integration
- Camera access for workout form analysis
- Geolocation improvements
- Battery-aware features

## Deployment

### Production Build
1. Minify HTML, CSS, and JavaScript
2. Optimize images and assets
3. Update service worker cache version
4. Deploy to HTTPS-enabled server
5. Test PWA installation and offline functionality

### CDN Considerations
- Chart.js and Leaflet are loaded from CDNs
- Consider self-hosting for better performance
- Implement proper CORS headers
- Monitor CDN uptime and fallback strategies

## API Integration

The frontend communicates with the FastAPI backend at `http://127.0.0.1:8000` via RESTful endpoints:

- `GET /activities` - Live telemetry data
- `GET /stats` - Session statistics
- `GET /sessions` - Session history
- `POST /recovery/log` - Log recovery metrics
- `GET /recovery/trend` - Recovery trends
- `GET /recovery/readiness-forecast` - Readiness prediction
- `GET /export` - CSV data export

All requests include JWT authentication headers.