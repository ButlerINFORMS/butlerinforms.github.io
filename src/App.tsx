import React from 'react';
import './styles/butler-theme.css';
import Header from './components/Header';

const App: React.FC = () => {
    return (
        <div className="App">
            <Header />
            <main>
                <h1>Welcome to the INFORMS Student Chapter at Butler University</h1>
                <p>This is a platform for students interested in operations research and analytics.</p>
            </main>
        </div>
    );
};

export default App;