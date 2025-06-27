import React from 'react';
import { Vortex } from 'react-loader-spinner';
import './Loading.css';

const Loading = ({ title, subtext }) => {
  return (
    <div className="loading-container-component">
      <div className="loading-content">
        <Vortex
          visible={true}
          height="80"
          width="80"
          ariaLabel="vortex-loading"
          wrapperStyle={{}}
          wrapperClass="vortex-wrapper"
          colors={['var(--fpl-green)', 'var(--fpl-green)', 'var(--fpl-green)', 'var(--fpl-green)', 'var(--fpl-green)', 'var(--fpl-green)']}
        />
        <h2 className="loading-title">{title}</h2>
        {subtext && <p className="loading-subtext">{subtext}</p>}
      </div>
    </div>
  );
};

export default Loading; 