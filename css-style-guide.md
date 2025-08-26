
# Retro Terminal UI Style Guide

## Design Philosophy
This style guide creates a retro computer terminal aesthetic reminiscent of early 1990s command-line interfaces and system control panels.

## Color Palette

### Primary Colors
```css
:root {
  --primary-bg: #ffffff;           /* Main background - pure white */
  --primary-text: #000000;         /* Main text - pure black */
  --border-color: #000000;         /* All borders - pure black */
  --secondary-bg: #f8f8f8;         /* Light gray backgrounds */
  --button-bg: #f0f0f0;            /* Button backgrounds */
}
```

### Status Colors
```css
:root {
  --success-bg: #e0ffe0;           /* Success background - light green */
  --success-text: #008000;         /* Success text - dark green */
  --error-bg: #ffe0e0;             /* Error background - light red */
  --error-text: #800000;           /* Error text - dark red */
  --warning-text: #ff8800;         /* Warning orange */
}
```

## Typography

### Font Family
**Primary Font**: `"Courier New", monospace`
- Use exclusively for all text elements
- Monospace ensures consistent character spacing
- Gives authentic terminal feel

### Font Sizes
```css
.system-title { font-size: 18px; }        /* Main headings */
.section-title { font-size: 14px; }       /* Section headers */
.normal-text { font-size: 12px; }         /* Default body text */
.button-text { font-size: 11px; }         /* Button labels */
.small-text { font-size: 10px; }          /* Helper text, captions */
.tiny-text { font-size: 9px; }            /* Very small labels */
```

### Text Decoration
```css
.section-title {
  font-weight: bold;
  text-decoration: underline;
}

.system-title {
  font-weight: bold;
  text-decoration: underline;
}
```

## Layout Structure

### Container Styling
```css
body {
  font-family: "Courier New", monospace;
  background-color: #ffffff;
  color: #000000;
  margin: 20px;
  font-size: 12px;
}

.header {
  border: 2px solid #000000;
  padding: 10px;
  margin-bottom: 20px;
}

.section {
  border: 1px solid #000000;
  padding: 15px;
  margin-bottom: 15px;
}
```

## Interactive Elements

### Buttons
```css
button {
  background-color: #f0f0f0;
  border: 2px outset #f0f0f0;      /* 3D raised effect */
  padding: 5px 15px;
  font-family: "Courier New", monospace;
  font-size: 11px;
  cursor: pointer;
  margin: 2px;
}

button:active {
  border: 2px inset #f0f0f0;       /* 3D pressed effect */
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
```

### Form Elements
```css
select, input[type="text"], input[type="password"] {
  font-family: "Courier New", monospace;
  font-size: 11px;
  border: 2px inset #f0f0f0;       /* 3D sunken effect */
  padding: 2px;
  background-color: #ffffff;
}
```

## Data Display

### Tables
```css
table {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
}

td, th {
  border: 1px solid #000000;
  padding: 5px;
  text-align: left;
  font-size: 11px;
}

th {
  background-color: #e0e0e0;
  font-weight: bold;
}
```

### Output/Console Areas
```css
.output {
  border: 1px solid #000000;
  background-color: #f8f8f8;
  padding: 10px;
  font-family: "Courier New", monospace;
  font-size: 10px;
  white-space: pre-wrap;
  height: 200px;
  overflow-y: scroll;
}
```

## Status Indicators

### Status Boxes
```css
.admin-status {
  padding: 5px;
  margin: 10px 0;
  border: 1px solid #000000;
  background-color: #f0f0f0;
  font-size: 10px;
}

.locked {
  background-color: #ffe0e0;
  color: #800000;
}

.unlocked {
  background-color: #e0ffe0;
  color: #008000;
}
```

### Status Text Colors
```css
.status-online { color: green; }
.status-error { color: red; }
.status-warning { color: orange; }
```

## Modal/Popup Styling

### Overlay and Popup
```css
.popup-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.5);
  z-index: 1000;
}

.popup {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: #ffffff;
  border: 2px solid #000000;
  padding: 20px;
  width: 300px;
  font-family: "Courier New", monospace;
}

.popup-title {
  font-weight: bold;
  text-decoration: underline;
  margin-bottom: 15px;
}
```

## Design Principles

### 1. Consistent Borders
- All major containers use `border: 1px solid #000000` or `border: 2px solid #000000`
- Buttons use `2px outset/inset` for 3D effect
- Form inputs use `2px inset` for sunken appearance

### 2. Spacing Standards
```css
/* Standard margins and padding */
.container-padding { padding: 15px; }
.section-margin { margin-bottom: 15px; }
.element-margin { margin: 10px 0; }
.small-margin { margin: 5px 0; }
.button-margin { margin: 2px; }
```

### 3. Color Usage Rules
- **Black borders only**: Never use colored borders
- **White backgrounds**: Primary containers always white
- **Light gray accents**: Use #f8f8f8 or #f0f0f0 for subtle backgrounds
- **Status colors**: Only for success/error states, never decorative

### 4. Typography Rules
- **One font family**: Always "Courier New", monospace
- **Bold + underline**: For all section titles and headers
- **Size hierarchy**: Stick to defined font sizes (9px, 10px, 11px, 12px, 14px, 18px)
- **No fancy formatting**: No shadows, gradients, or modern effects

### 5. Interactive Feedback
```css
/* Hover states should be minimal */
button:hover {
  background-color: #e8e8e8;
}

/* Focus states for accessibility */
input:focus, select:focus {
  outline: 2px solid #000000;
  outline-offset: 1px;
}
```

## Layout Patterns

### System Header Pattern
```css
.system-header {
  border: 2px solid #000000;
  padding: 10px;
  margin-bottom: 20px;
  background-color: #ffffff;
}

.system-header h2 {
  font-size: 18px;
  font-weight: bold;
  text-decoration: underline;
  margin: 0 0 10px 0;
}
```

### Control Section Pattern
```css
.control-section {
  border: 1px solid #000000;
  padding: 15px;
  margin-bottom: 15px;
  background-color: #ffffff;
}

.section-title {
  font-weight: bold;
  text-decoration: underline;
  margin-bottom: 10px;
  font-size: 14px;
}
```

### Form Layout Pattern
```css
.form-table {
  width: 100%;
  margin: 10px 0;
}

.form-table td:first-child {
  width: 150px;
  font-weight: normal;
}

.form-table select,
.form-table input {
  width: 200px;
}
```

## Animation Guidelines
- **Minimal animations**: This is a retro terminal interface
- **No smooth transitions**: Instant state changes only
- **3D button effects**: Only on :active pseudo-class
- **No hover animations**: Keep interactions simple and immediate

## Accessibility Notes
- High contrast (black on white) ensures readability
- Monospace font aids users with dyslexia
- Clear focus indicators for keyboard navigation
- Status colors have sufficient contrast ratios
- Text size minimum of 10px for readability

## Usage Examples

### Basic Page Structure
```html
<body>
  <div class="header">
    <h2>SYSTEM NAME v1.0</h2>
    <p>Status: <span class="status-online">ONLINE</span></p>
  </div>
  
  <div class="section">
    <div class="section-title">SECTION NAME</div>
    <!-- Content here -->
  </div>
</body>
```

### Form Pattern
```html
<form>
  <table class="form-table">
    <tr>
      <td>Field Label:</td>
      <td>
        <select required>
          <option>-- SELECT OPTION --</option>
        </select>
      </td>
    </tr>
    <tr>
      <td>Action:</td>
      <td>
        <button type="submit">EXECUTE</button>
      </td>
    </tr>
  </table>
</form>
```

This style guide captures the essence of your retro terminal interface and provides clear guidelines for replicating the aesthetic consistently across any application.
