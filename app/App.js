/**
 *
 * @format
 * @flow
 */
1;
import React, { Component } from "react";
import { StyleSheet, Text, View, Alert, Button, ActivityIndicator } from "react-native";

import RippledWsClient from "rippled-ws-client";
import RippledWsClientSign from "rippled-ws-client-sign";

const ACCOUNT_ADDRESS = "r3xcFjD6t3SwZDkER3sgehmKuYXuM8R3ez";
const ACCOUNT_SECRET = "shAUGqSFm3eY6D1Ppc5bQ5CptQBTN";
const wsURL = "wss://s.altnet.rippletest.net:51233";

type Props = {};
export default class App extends Component<Props> {
    constructor(props){
        super(props)

        this.state = {
            loading: false
        }
    }
    async send_command(command) {
        const Transaction = {
            TransactionType: "Payment",
            Account: ACCOUNT_ADDRESS,
            Destination: 'rpEPpEr5ED6NzykYunBEJJoMdfjp1t3uf4',
            Amount: '100',
            Memos:[
                {
                  Memo: {
                    MemoType: Buffer.from('IOT_COMMAND', 'utf8').toString('hex').toUpperCase(),
                    MemoData: Buffer.from(`${command}`, 'utf8').toString('hex').toUpperCase()
                  }
                }
            ] ,
            LastLedgerSequence: null,
        };

        this.setState({
            loading: true
        })

        await new RippledWsClient(wsURL)
            .then(Connection => {
                return new RippledWsClientSign(Transaction, ACCOUNT_SECRET, Connection)
                    .then(TransactionSuccess => {
                        Connection.close();
                        this.setState({
                            loading: false
                        })
                        Alert.alert("Success", `Sent command '${command}' with TX ${TransactionSuccess.hash}`);
                    })
                    .catch(SignError => {
                        return {
                            resultCode: "error",
                            error: SignError.details,
                        };
                    });
            })
            .catch(ConnectionError => {
                return {
                    resultCode: "error",
                    error: ConnectionError,
                };
            });
    }

    render() {
        const { loading } = this.state

        if(loading){
            return (
                <View style={styles.container}>
                    <Text style={styles.instructions}>Sending transaction to XRP Ledger</Text>
                    <Text style={styles.welcome}>Please wait ...</Text>
                    <ActivityIndicator size="large" color="#0000ff" />
                </View>
            )
        }else{
            return (
                <View style={styles.container}>
                    <Text style={styles.welcome}>XRPL IOT</Text>
                    <Text style={styles.instructions}>Send commands to IOT devices through XRP Ledger</Text>
                    <View style={{marginTop:50}}>
    
                        <Button
                            onPress={() => {this.send_command('turn_on')}}
                            title="Turn On Led"
                            color="green"
                        />
                    </View>
    
                    <View style={{marginTop:30}}>
                        <Button
                        
                            onPress={() => {this.send_command('turn_off')}}
                            title="Turn Off Led"
                            color="red"
                        />
                    </View>
                    
                </View>
            );
        }
   
    }
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        justifyContent: "center",
        alignItems: "center",
        backgroundColor: "#F5FCFF",
    },
    welcome: {
        fontSize: 20,
        textAlign: "center",
        margin: 10,
    },
    instructions: {
        textAlign: "center",
        color: "#333333",
        marginBottom: 5,
    },
});
