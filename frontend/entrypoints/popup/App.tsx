import { useState } from 'react';
import reactLogo from '@/assets/react.svg';
import wxtLogo from '/wxt.svg';
import './App.css';

import { Button } from '../../components/button';

function App() {
  const [count, setCount] = useState(0);

  return (
    <>
      <h1>Rezmaker</h1>
      <div className="card">
        <Button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </Button>
      </div>
    </>
  );
}

export default App;
