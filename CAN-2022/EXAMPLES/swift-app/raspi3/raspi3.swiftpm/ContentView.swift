import SwiftUI

struct ContentView: View {
    var body: some View {
        NavigationView {
            VStack {
                Text("BOBIK")
                    .font(.largeTitle)
                    .padding()
                
                NavigationLink(destination: WebPage(urlString: "http://bobik.lan:8080/status"), label: {
                    CustomButton(label: "Status")
                })
                
                NavigationLink(destination: WebPage(urlString: "http://bobik.lan:8080/arm"), label: {
                    CustomButton(label: "Arm")
                })
                
                NavigationLink(destination: WebPage(urlString: "http://bobik.lan:8080/disarm"), label: {
                    CustomButton(label: "Disarm")
                })
                
                Spacer()
            }
            .navigationBarHidden(true)
        }
    }
}

struct WebPage: View {
    let urlString: String
    
    var body: some View {
        WebView(urlString: urlString)
            .navigationBarTitle("", displayMode: .inline)
    }
}

struct CustomButton: View {
    let label: String
    
    var body: some View {
        Text(label)
            .font(.headline)
            .foregroundColor(.white)
            .padding()
            .background(Color.blue)
            .cornerRadius(10)
            .padding(.horizontal)
            .padding(.vertical, 5)
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
