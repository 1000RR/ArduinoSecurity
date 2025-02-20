"use client";
import AppView from '@components/AppView';
import { Provider } from 'react-redux';
import store from '@store/store';

const App: React.FC = () => {	
	return (<Provider store={store}>
		<AppView></AppView>
	</Provider>);
};

export default App;