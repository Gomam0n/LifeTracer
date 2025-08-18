// English Language Pack
window.LANG_DATA = {
    // Page title and main content
    page: {
        title: "LifeTracer - Historical Figure Life Trajectory Tracker",
        heading: "LifeTracer - Historical Figure Life Trajectory Tracker",
        description: "Enter a person's name to get geographical coordinates of important locations in their life"
    },

    // Input section
    input: {
        label: "Enter person's name:",
        placeholder: "e.g., Abraham Lincoln, Isaac Newton, Einstein, etc.",
        button: "Get Life Trajectory"
    },

    // Status messages
    status: {
        loading: "Querying life trajectory, please wait...",
        success: "Query successful!",
        error: "Query failed, please try again"
    },

    // Error messages
    error: {
        network: "Network connection failed, please check your network settings",
        server: "Server error, please try again later",
        notFound: "No biographical information found for this person",
        validation: "Input validation failed, please check the name format",
        invalidInput: "Please enter a valid person's name",
        timeout: "Request timeout, please try again",
        unknown: "Unknown error, please contact administrator"
    },

    // Results display
    result: {
        title: "Life Trajectory Results",
        noData: "No data available",
        coordinate: "Coordinates",
        description: "Description",
        location: "Location",
        time: "Time",
        event: "Event"
    },

    // Map related
    map: {
        title: "Life Trajectory Map",
        loading: "Loading map...",
        error: "Failed to load map",
        noData: "No trajectory data available",
        stats: {
            title: "Trajectory Statistics",
            totalLocations: "Total locations: {count}",
            totalDistance: "Total distance: approximately {distance} km",
            timeSpan: "Time span: {span}",
            regions: "Regions covered: {regions}"
        },
        popup: {
            location: "Location: {location}",
            time: "Time: {time}",
            event: "Event: {event}",
            coordinates: "Coordinates: {lat}, {lng}"
        },
        controls: {
            zoomIn: "Zoom In",
            zoomOut: "Zoom Out",
            reset: "Reset View",
            fullscreen: "Fullscreen"
        }
    },

    // Common text
    common: {
        loading: "Loading...",
        retry: "Retry",
        close: "Close",
        confirm: "Confirm",
        cancel: "Cancel",
        save: "Save",
        delete: "Delete",
        edit: "Edit",
        view: "View",
        back: "Back",
        next: "Next",
        previous: "Previous",
        submit: "Submit",
        reset: "Reset",
        clear: "Clear",
        search: "Search",
        filter: "Filter",
        sort: "Sort",
        export: "Export",
        import: "Import",
        help: "Help",
        about: "About",
        settings: "Settings"
    },

    // Time format
    time: {
        year: "year",
        month: "month",
        day: "day",
        hour: "hour",
        minute: "minute",
        second: "second",
        ago: "ago",
        later: "later",
        now: "now",
        today: "today",
        yesterday: "yesterday",
        tomorrow: "tomorrow"
    },

    // Units
    units: {
        kilometer: "km",
        meter: "m",
        mile: "mile",
        foot: "ft",
        degree: "°",
        percent: "%"
    },

    // Tips
    tips: {
        inputHelp: "Please enter the name of the historical figure you want to query",
        mapHelp: "Click on map markers to view detailed information",
        languageSwitch: "Click the top-right corner to switch language",
        mobileOptimized: "This application is optimized for mobile devices"
    }
};