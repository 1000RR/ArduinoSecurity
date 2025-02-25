"use client";
import AppView from '@components/AppView';
import { Provider } from 'react-redux';
import store from '@store/store';
import { useEffect } from 'react';

const App: React.FC = () => {	
	useEffect(() => {
		if ('serviceWorker' in navigator) {
		  window.addEventListener('load', () => {
			navigator.serviceWorker.register('/serviceworker.js')
			  .then(registration => {
				console.log('Service Worker registered with scope:', registration.scope);
			  })
			  .catch(error => {
				console.error('Service Worker registration failed:', error);
			  });
		  });
		}
	  }, []);
	  
	return (<Provider store={store}>
		<AppView></AppView>
	</Provider>);
};

export default App;