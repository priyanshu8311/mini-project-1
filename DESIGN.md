# Visual direction and design principles

**Clarity and trust:** Use a clean, professional style that highlights real-time data. Show stock levels, alerts, and statuses plainly so users trust the information【8†L62-L69】【47†L183-L186】. For example, the inventory UI should display item status, location, quantity, and demand flags together, with clear labels and alerts【8†L62-L69】【47†L183-L186】. **Task-focused workflows:** Align each screen to a specific task. E.g. a Receiving screen emphasizes purchase order details, expected units, and gap alerts, while a Picking screen emphasizes bin locations, swap options, and priority flags【47†L139-L142】. Keep navigation shallow so common actions are accessible in 1–2 clicks【47†L169-L173】. **Role-based views:** Customize views for different roles. Warehouse staff see task orders, bin locations, and scan feedback; buyers/planners see vendor lead times, reorder points, and risk indicators【47†L139-L142】【47†L193-L196】. Ensure each role has the “right detail”: e.g. pickers see count and spot, buyers see supplier data【47†L193-L196】. **Actionable dashboards:** Highlight key metrics (e.g. low-stock alerts, predicted demand spikes, overstock warnings) and prioritize what needs attention【45†L454-L459】. Dashboards should answer “what needs action now,” showing only a few critical KPIs in cards or charts【45†L454- L459】. Avoid clutter – focus on top-priority flags first (e.g. out-of-stock items, urgent orders). **Consistency and simplicity:** Use consistent layouts and elements. Minimize excess decoration; every control or visual should serve a purpose. Follow a neutral color palette with subtle accents (see Colors) and a uniform grid (see Spacing). Use clear typography and iconography, and avoid unnecessary animations. Overall, the UI should enable users to work faster and with fewer errors 【8†L62-L69】【44†L72-L79】.

# Colors and typography

**Color palette:** Use the 60-30-10 rule【24†L140-L149】. For example, 60% neutral light backgrounds (e.g. shades of off-white or light gray), 30% secondary (text and panels), and 10% accent (primary buttons, links, highlights). Primary brand color (e.g. blue) for main actions, secondary accent (e.g. green) for positive status, and a warning (orange) or error (red) for alerts. Ensure all text/background combinations meet WCAG 2.2 AA contrast (≥4.5:1)【29†L19-L28】. Never convey meaning by color alone – always pair with icons or text【29†L24-L28】. Test with color-blindness simulators to catch issues【29†L24-L28】. **Semantic colors:** Define semantic tokens: e.g. color-success (green), color-error (red), color-warning (amber), color-info (blue). Use these consistently for status messages, badges, or alerts. For example, show “In Stock” in green and “Out of Stock” in red. Always include textual feedback (like “Low stock” label with red icon) so users aren’t relying on color only. **Typography:** Use a single sans-serif family (e.g. system font stack or a font like Inter/Roboto). Set a clear hierarchy: for example, H1=24-32px (page titles), H2=20px (section titles), H3=16px, etc. Body text should be at least 14px or 16px with line height ~1.4–1.6 for readability. Use bold or medium weights to highlight labels or section headings. Avoid large decorative fonts or too many variations. Ensure consistent letter spacing and sizing across components.

•

•

•

•

•

•

•

•

**Font colors:** Primary text should be dark gray (near black). Secondary or disabled text can be medium gray. Links/buttons use accent color. Maintain high contrast for readability【29†L19-L28】. **Buttons and controls:** Primary buttons use the accent color (e.g. blue) with white text, secondary buttons are outlined or neutral gray. Disabled buttons should be low-contrast gray. Use consistent border radii (e.g. 4px) and padding (e.g. 12px vertically) for all buttons. For emphasis, use size (primary button larger, secondary smaller).

# Spacing and layout system

**8-point grid:** Adopt an 8px base unit【28†L30-L38】. All padding, margin, and gaps are multiples of 8px (with 4px allowed for tight elements like icon spacing)【28†L30-L38】. This simplifies consistency and snapping on high-DPI screens. **Spacing scale:** Define reusable spacing tokens (e.g. xs=4px, sm=8px, md=16px, lg=24px, xl=32px, 2xl=48px, 3xl=64px)【28†L58-L66】. Use --space-md (16px) for standard padding inside cards/ forms; --space-lg (24px) to separate form sections; --space-xl (32px) between page sections; larger (48-64px) for major page gaps【28†L58-L66】. Do not introduce arbitrary pixel values outside this scale. **Layout grid:** Use a responsive 12-column grid (or similar) for page layouts. On desktop, content can span up to 12 cols; on tablet, reduce columns and stack on mobile. Maintain consistent gutter (column gap) of 16px–24px. Center content in the viewport with max width (e.g. 1200px) and horizontal margins auto. **Whitespace:** Provide generous whitespace to group related items. For example, card padding = 16px ( space-md ), sections separated by 32px ( space-xl ). Form fields in a group may have 16px between them, and 32px between distinct form sections. Tables have 16px above/below; filter sidebar items have 8–16px gap. Whitespace improves scan-ability and grouping. **Responsive spacing:** On smaller screens, reduce side margins (e.g. 16px) and stack columns vertically, but maintain at least one standard gap between components. Do not let elements touch the edges of the screen.

# Reusable components

**Navigation (Header/Sidebar):** A top app bar or left sidebar holds global navigation. Use a fixed height header (e.g. 60px) with logo/brand, page title, and user menu. The sidebar (if used) is fixed width (240px), with sections (icons + labels). Active link is highlighted with background or accent border. Collapsible icons-only mode should preserve recognizable icons. Ensure keyboard access (focus outline) on nav items. **Buttons:** Define Primary (filled accent color), Secondary (outline or gray fill), Tertiary (text link style), and Icon buttons (only icon, e.g. 24px size). All buttons have the same corner radius and padding. Disabled state is grayed out. Hover states are subtle (e.g. darken the background by 5–10%). **Form controls:** Text inputs, selects, checkboxes, radios, toggles use consistent styles. Labels sit above fields (left-aligned). Required fields show asterisk. Field height ~40px with 8px padding. Error state: red border + error message text (small, red) below field. Provide helper text or icons as needed. Use placeholder text only as examples, not labels. Group related fields in a section card or fieldset with a small header. **Data tables:** Used for inventory lists, orders, logs. Header row with clear column labels and sort icons. Row hover highlights background lightly. Use zebra striping or alternating row colors

•

•

•

•

•

•

•

•

•

•

•

sparingly. Include checkboxes for multi-select in first column. Fit table in container with horizontal scroll on small screens or allow column reflow. **Cards/Panels:** For dashboards or item details, use card containers with slight shadow or border. Each card has a header (title) and body. Use consistent padding inside cards. Cards may contain KPI metrics, charts, or lists. Ensure cards align to grid. **Charts/Graphs:** Use a library (e.g. Chart.js, D3) with color tokens matching the palette. For example, use accent color for main data lines/bars, a lighter accent for projections, gray for background grid. Always label axes and lines. Include legend or tooltip for clarity. **Modals/Dialogs:** Centered overlay with semi-transparent dark background. Modal width responsive (e.g. max 600px). Title at top, close (X) in corner. Footer for actions (Confirm/Cancel). Use same button styles. Modal opening/closing uses a quick fade or scale animation. **Toasts/Alerts:** Non-blocking notifications (e.g. “Saved”, “Error”) appear at top or bottom. Use distinct color borders or backgrounds (green for success, red for error). Auto-dismiss after a few seconds. Ensure screen-reader-friendly (aria-live). **Search & Filters:** Global search box (in header or nav) that can query SKU/name. Filter sidebar or top-bar filters use dropdowns, date pickers, and multi-select toggles. “Apply/Reset” buttons at bottom of filter panel.

# Navigation and forms

**Global navigation:** Show key sections: Dashboard, Inventory, Orders, Forecast, Reports, Settings. Highlight current section. On mobile, collapse into a hamburger menu or bottom tab bar. Provide breadcrumbs on deep pages (e.g. Inventory > Widget A) to orient users. Keep menu structure shallow. **Primary actions:** Use a consistent primary action button (e.g. “+ Add Item” or “New Forecast”) at top of pages or lists. Secondary actions (e.g. “Upload CSV”) should be nearby but styled less prominently. **Forms:** Layout forms top-to-bottom in logical groupings. For example, an inventory item form might have Item Info, Stock Details, and Vendor Info sections. Always label fields clearly. Indicate required fields. Provide inline validation hints (e.g. “Must be unique”) and summary error list on submit if needed. **Inline editing:** In tables or details views, allow inline edits for speed (e.g. editable quantity cells). Use proper affordances (pencil icon). Confirm changes or allow single-click edits. **Accessible forms:** Link <label> to inputs, use ARIA if needed (e.g. aria-invalid ). Place placeholder text judiciously (avoid as substitute for labels). Use fieldsets for radio groups.

# Loading, empty, and error states

**Loading:** While fetching data, show a spinner or animated skeleton UI. For tables, display grey row placeholders. For charts, display a skeleton graph outline. This indicates progress【44†L72-L79】. Don’t leave blank space. If load is prolonged, show a progress bar or message (“Loading orders…”). **Empty states:** When lists or dashboards have no data, show a friendly message and, if possible, an illustration or icon (e.g. box icon for empty inventory). Explain the empty state (e.g. “No inventory items found”) and offer a clear action (e.g. “Add New Item”). Keep copy concise and helpful. Empty state should not feel like an error. **Error states:** If an error occurs (network or form validation), display a visible alert banner (red or amber) with a short message (“Failed to save. Please try again.”) and actions (e.g. “Retry” button).

•

•

•

•

•

•

•

•

•

•

•

•

•

Highlight the field(s) in error. For page-level errors, show an error page with error code/message and a link to retry or contact support. Ensure error messages are clear and actionable.

# Interactions and animations

**Hover/focus states:** All interactive elements (buttons, links, table rows) should have a visible hover and focus state (e.g. slight background tint or border). Focus outlines should meet accessibility contrast. **Transitions:** Use subtle transitions (150–200ms ease) for UI changes (modals, page switches, dropdowns). Avoid anything jarring. For buttons, a quick opacity or transform on press (50–100ms) gives feedback. Do **not** use long or looping animations. **System feedback:** Provide immediate feedback for user actions. For instance, after clicking “Save”, show a spinner or disable the button, then show a toast “Saved successfully” on completion 【44†L72-L79】. For form submissions, highlight invalid fields. **Microinteractions:** Use microinteractions to confirm system status or errors【44†L72-L79】. E.g., when scanning a barcode, show a green flash or checkmark on success and a sound, or show “Item not found” text on failure【45†L372-L379】. Toasts or modals can slide down/up briefly. Keep microinteractions consistent (same style of transition for similar actions). **Animations:** Use sparingly. A brief fade for tooltips or slide for panels is fine. Avoid parallax or decorative animations. Ensure any movement can be reduced (check prefers-reduced-motion ).

# Responsive behavior

**Mobile layout:** Collapse sidebar to a top hamburger menu or bottom nav bar. Use single-column layouts: cards stack vertically, tables become scrollable or transform into card lists. Ensure buttons and inputs are touch-friendly (min 44px tap targets). **Mobile scanning tasks:** For scanning or picking on handhelds, each screen does one task. Use large buttons/inputs, minimal text. On a successful scan show immediate feedback (green highlight or checkmark)【45†L372-L379】. On error, show large plain-text message (e.g. “Barcode not recognized”)【45†L372-L379】. **Breakpoint guidelines:** Typical breakpoints: ≥1200px (desktop), 768–1199px (tablet), <768px (mobile). At tablet width, collapse sidebars or reduce columns (e.g. 2-column to 1-column). Hide nonessential text or use popovers if space is tight. **Data reflow:** Tables may allow horizontal scroll on small screens. Charts should be responsive (maintain aspect ratio, adjust labels). Use vertical scroll for long lists. Avoid horizontal scrolling of the whole page. **Consistent UX:** Keep all functionality on mobile (no separate mobile app required). Preserve feature parity (forms, filters), but adapt UI. E.g., a filter panel becomes an overlay on mobile instead of sideby-side.

# Accessibility requirements

**Contrast & Color:** Follow WCAG 2.2 AA: text ≥4.5:1 contrast (or 3:1 for large text)【29†L19-L28】. Use color contrast checkers. Do not rely on color alone for information【29†L24-L28】.

•

•

•

•

•

•

•

•

•

•

•

**Keyboard navigation:** All interactive elements reachable via Tab. Use visible focus indicators. Ensure menu navigation works with keyboard and that shortcuts are logical. **ARIA and semantics:** Use semantic HTML (buttons, forms). For custom components, include appropriate role and aria-* attributes (e.g. role="dialog" for modals, aria-expanded on menus). Provide alt text for images/icons or mark them decorative ( aria-hidden="true" ). **Forms:** Associate every input with a <label> or aria-label . Include aria-describedby for hints and error messages. Alert messages (toasts, banners) should use aria-live="polite" or "assertive" . **Text sizing:** Allow browser zoom up to 200%. Avoid absolute units (px) for text; use rem/em where feasible. Use readable fonts. **Reduced motion:** Respect the user’s prefers-reduced-motion setting. Disable non-essential animations (e.g. smooth page transitions) if enabled. **Language and readability:** Mark the document language. Use simple, clear language (no jargon) for UI text. **Testing:** Regularly test with screen readers (e.g. NVDA, VoiceOver) and keyboard-only navigation.

# Page-level layout guidance

**Header:** Always include a global header with application name/logo (clickable to Dashboard), search bar, and user avatar/menu. Place global actions (notifications, help) here. The header background should contrast with content. **Sidebar (if used):** On desktop, a fixed left sidebar lists main sections with icons+labels. Group related links (e.g. under “Inventory”, “Orders”). The sidebar background can be a dark neutral; text/ icons light gray. Collapsed (icon-only) mode still shows tooltips on hover. **Content container:** Content pages should have a clear title and optional breadcrumbs. Use a consistent max-width (e.g. 1200px) and center the content. Add padding (~16px) around content. Section headings (H2/H3) separate page blocks. **Section structure:** Use cards or panels for distinct content blocks (e.g. KPI cards in a grid, inventory table in a card). Each card has a header and a body. Align card headers in each row. In forms, wrap fields in a card or fieldset with a heading. **Footer:** Optional. If present, keep it minimal (about 40px height) with copyright or version info. **Examples:** **Dashboard:** Shows a row of KPI cards (in a grid), followed by charts and recent activity. Possibly a two-column grid on desktop that collapses to one column on mobile. **Inventory list:** Full-width table with filters above. “Add Item” button top-right. Pagination at bottom. **Item details:** Two-column layout (details on left, actions on right) or tabs (General / History / Forecast). **Forms:** Centered card with title. Fields stacked vertically, submit button at bottom. On wide screens, form groups side-by-side if it fits (2 columns). **Consistency:** Ensure similar pages use the same layout pattern (e.g. all list pages have filter sidebar and table). This builds familiarity and speed.

**Assumptions:** No specific brand style was provided, so neutral corporate styling is used. Designs assume a desktop-first application with mobile support. Additional branding (logos, colors) can be integrated per client needs.

•

•

•

•

•

•

•

•

•

•

•

• • •

• •

•

•